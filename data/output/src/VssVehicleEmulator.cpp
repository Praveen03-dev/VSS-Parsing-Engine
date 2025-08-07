/*
 * Copyright (C) 2024 The Android Open Source Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#define LOG_TAG "VssVehicleEmulator"

#include "VssVehicleEmulator.h"
#include "AndroidVssConverter.h"
#include "VssSocketComm.h"

#include <android-base/logging.h>
#include <sstream>
#include <chrono>

namespace android {
namespace hardware {
namespace automotive {
namespace vehicle {
namespace V2_0 {
namespace impl {

VssVehicleEmulator::VssVehicleEmulator(VehicleHalManager* vhalManager)
    : VehicleEmulator(vhalManager), 
      mInitialized(false), 
      mActive(false) {
    LOG(INFO) << "VssVehicleEmulator constructed";
}

VssVehicleEmulator::~VssVehicleEmulator() {
    shutdown();
    LOG(INFO) << "VssVehicleEmulator destroyed - Messages processed: " << mMessagesProcessed.load()
              << ", Converted: " << mMessagesConverted.load()
              << ", Errors: " << mConversionErrors.load();
}

bool VssVehicleEmulator::initialize() {
    std::lock_guard<std::mutex> lock(mVssLock);
    
    if (mInitialized) {
        LOG(WARNING) << "VssVehicleEmulator already initialized";
        return true;
    }

    LOG(INFO) << "Initializing VssVehicleEmulator...";

    try {
        // Initialize the VSS to VHAL converter
        mVssConverter = std::make_unique<AndroidVssConverter>();
        if (!mVssConverter->initialize()) {
            LOG(ERROR) << "Failed to initialize AndroidVssConverter";
            return false;
        }

        // Create shared_ptr to this object for VssSocketComm
        std::shared_ptr<VssMessageProcessor> processor = 
            std::shared_ptr<VssMessageProcessor>(this, [](VssMessageProcessor*) {
                // Custom deleter that does nothing since this object manages its own lifetime
            });

        // Initialize the socket communication
        mSocketComm = std::make_unique<VssSocketComm>(processor);
        if (!mSocketComm->start()) {
            LOG(ERROR) << "Failed to start VssSocketComm";
            return false;
        }

        mInitialized = true;
        mActive = true;
        
        LOG(INFO) << "VssVehicleEmulator initialization complete";
        LOG(INFO) << "VSS converter initialized with " << mVssConverter->getMappingCount() << " signal mappings";
        return true;
        
    } catch (const std::exception& e) {
        LOG(ERROR) << "Exception during VssVehicleEmulator initialization: " << e.what();
        return false;
    }
}

void VssVehicleEmulator::shutdown() {
    std::lock_guard<std::mutex> lock(mVssLock);
    
    if (!mInitialized) {
        return;
    }

    LOG(INFO) << "Shutting down VssVehicleEmulator...";
    
    mActive = false;
    
    // Stop socket communication
    if (mSocketComm) {
        mSocketComm->stop();
        mSocketComm.reset();
    }
    
    // Cleanup converter
    if (mVssConverter) {
        mVssConverter.reset();
    }
    
    mInitialized = false;
    
    LOG(INFO) << "VssVehicleEmulator shutdown complete";
}

bool VssVehicleEmulator::isActive() const {
    std::lock_guard<std::mutex> lock(mVssLock);
    return mActive && mInitialized;
}

void VssVehicleEmulator::processVssMessage(const std::string& message) {
    if (!isActive()) {
        LOG(WARNING) << "VssVehicleEmulator not active, ignoring message: " << message;
        return;
    }

    mMessagesProcessed++;
    
    LOG(VERBOSE) << "Processing VSS message: " << message;
    
    try {
        std::string vssPath, vssValue;
        if (!parseVssMessage(message, vssPath, vssValue)) {
            LOG(WARNING) << "Failed to parse VSS message: " << message;
            mConversionErrors++;
            return;
        }

        // Convert VSS data to VHAL format
        VehiclePropValue propValue;
        if (!mVssConverter->convertVssToVhal(vssPath, vssValue, propValue)) {
            LOG(WARNING) << "Failed to convert VSS signal: " << vssPath << "=" << vssValue;
            mConversionErrors++;
            return;
        }

        // Update the VHAL property store
        if (updateVhalProperty(propValue)) {
            mMessagesConverted++;
            LOG(DEBUG) << "Successfully processed VSS signal: " << vssPath 
                      << " -> VHAL property " << std::hex << propValue.prop;
        } else {
            LOG(ERROR) << "Failed to update VHAL property for VSS signal: " << vssPath;
            mConversionErrors++;
        }
        
    } catch (const std::exception& e) {
        LOG(ERROR) << "Exception processing VSS message '" << message << "': " << e.what();
        mConversionErrors++;
    }
}

bool VssVehicleEmulator::parseVssMessage(const std::string& message, 
                                         std::string& vssPath, 
                                         std::string& vssValue) {
    // VSS messages are expected in format: "VSS.Path=Value"
    size_t equals_pos = message.find('=');
    if (equals_pos == std::string::npos || equals_pos == 0 || equals_pos == message.length() - 1) {
        LOG(WARNING) << "Invalid VSS message format (missing or misplaced '='): " << message;
        return false;
    }
    
    vssPath = message.substr(0, equals_pos);
    vssValue = message.substr(equals_pos + 1);
    
    // Trim whitespace
    vssPath.erase(vssPath.find_last_not_of(" \t\r\n") + 1);
    vssPath.erase(0, vssPath.find_first_not_of(" \t\r\n"));
    vssValue.erase(vssValue.find_last_not_of(" \t\r\n") + 1);
    vssValue.erase(0, vssValue.find_first_not_of(" \t\r\n"));
    
    if (vssPath.empty() || vssValue.empty()) {
        LOG(WARNING) << "Empty VSS path or value in message: " << message;
        return false;
    }
    
    return true;
}

bool VssVehicleEmulator::updateVhalProperty(const VehiclePropValue& propValue) {
    try {
        // Use the parent VehicleEmulator's functionality to update the property
        // This leverages the existing VHAL infrastructure
        StatusCode result = doSetProperty(propValue);
        
        if (result == StatusCode::OK) {
            // Also notify any subscribers using the VehicleHal manager
            if (mHal != nullptr) {
                mHal->setPropertyFromVehicle(propValue);
            }
            return true;
        } else {
            LOG(WARNING) << "VHAL property update failed with status: " << static_cast<int>(result)
                        << " for property " << std::hex << propValue.prop;
            return false;
        }
        
    } catch (const std::exception& e) {
        LOG(ERROR) << "Exception updating VHAL property " << std::hex << propValue.prop 
                  << ": " << e.what();
        return false;
    }
}

// VehicleEmulator interface implementations
void VssVehicleEmulator::doSetValueFromClient(const VehiclePropValue& propValue) {
    // Pass through to parent implementation
    VehicleEmulator::doSetValueFromClient(propValue);
}

void VssVehicleEmulator::doGetConfig(VehiclePropConfig* config) const {
    // Pass through to parent implementation  
    VehicleEmulator::doGetConfig(config);
}

void VssVehicleEmulator::doGetConfigNoLock(VehiclePropConfig* config) const {
    // Pass through to parent implementation
    VehicleEmulator::doGetConfigNoLock(config);
}

VehiclePropValue VssVehicleEmulator::doGetProperty(const VehiclePropValue& request) const {
    // Pass through to parent implementation
    return VehicleEmulator::doGetProperty(request);
}

StatusCode VssVehicleEmulator::doSetProperty(const VehiclePropValue& propValue) const {
    // Pass through to parent implementation with additional logging for VSS context
    LOG(VERBOSE) << "Setting VHAL property " << std::hex << propValue.prop 
                << " from VSS processing";
    return VehicleEmulator::doSetProperty(propValue);
}

}  // namespace impl
}  // namespace V2_0
}  // namespace vehicle
}  // namespace automotive
}  // namespace hardware
}  // namespace android
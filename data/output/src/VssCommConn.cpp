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

#define LOG_TAG "VssCommConn"

#include "VssCommConn.h"
#include "VssVehicleEmulator.h"

#include <android-base/logging.h>

namespace android {
namespace hardware {
namespace automotive {
namespace vehicle {
namespace V2_0 {
namespace impl {

VssCommConn::VssCommConn(std::shared_ptr<VssMessageProcessor> processor) 
    : mProcessor(processor) {
    LOG(INFO) << "VssCommConn constructed";
}

VssCommConn::~VssCommConn() {
    stop();
    LOG(INFO) << "VssCommConn destroyed";
}

void VssCommConn::processMessage(const std::string& message) {
    if (mProcessor && !message.empty()) {
        LOG(VERBOSE) << "Processing VSS message: " << message;
        mProcessor->processVssMessage(message);
    } else {
        LOG(WARNING) << "Cannot process message: " 
                     << (mProcessor ? "empty message" : "no processor");
    }
}

}  // namespace impl
}  // namespace V2_0
}  // namespace vehicle
}  // namespace automotive
}  // namespace hardware
}  // namespace android
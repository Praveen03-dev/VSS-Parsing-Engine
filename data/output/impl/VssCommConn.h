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

#pragma once

#include <thread>
#include <atomic>
#include <memory>

namespace android {
namespace hardware {
namespace automotive {
namespace vehicle {
namespace V2_0 {
namespace impl {

// Forward declaration
class VssMessageProcessor;

/**
 * Abstract base class for VSS communication connections.
 * This defines the contract for any communication channel that can
 * receive VSS messages and pass them to a message processor.
 */
class VssCommConn {
public:
    explicit VssCommConn(std::shared_ptr<VssMessageProcessor> processor);
    virtual ~VssCommConn();

    /**
     * Start the communication channel.
     * @return true if started successfully, false otherwise
     */
    virtual bool start() = 0;

    /**
     * Stop the communication channel.
     */
    virtual void stop() = 0;

    /**
     * Check if the communication channel is currently running.
     * @return true if running, false otherwise
     */
    virtual bool isRunning() const = 0;

protected:
    /**
     * Read data from the communication channel.
     * Implementations should override this method to handle specific protocols.
     */
    virtual void readLoop() = 0;

    /**
     * Process a received message by passing it to the message processor.
     * @param message Raw message string received from the communication channel
     */
    void processMessage(const std::string& message);

    std::shared_ptr<VssMessageProcessor> mProcessor;
    std::atomic<bool> mRunning{false};
    std::thread mReadThread;
};

}  // namespace impl
}  // namespace V2_0
}  // namespace vehicle
}  // namespace automotive
}  // namespace hardware
}  // namespace android
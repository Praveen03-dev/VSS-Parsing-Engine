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

#define LOG_TAG "VssSocketComm"

#include "VssSocketComm.h"
#include "VssVehicleEmulator.h"

#include <android-base/logging.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <unistd.h>
#include <fcntl.h>
#include <sstream>
#include <cstring>

namespace android {
namespace hardware {
namespace automotive {
namespace vehicle {
namespace V2_0 {
namespace impl {

VssSocketComm::VssSocketComm(std::shared_ptr<VssMessageProcessor> processor, int port)
    : VssCommConn(processor), 
      mPort(port), 
      mServerSocket(-1), 
      mClientSocket(-1) {
    LOG(INFO) << "VssSocketComm constructed for port " << mPort;
}

VssSocketComm::~VssSocketComm() {
    stop();
    LOG(INFO) << "VssSocketComm destroyed";
}

bool VssSocketComm::start() {
    if (mRunning.load()) {
        LOG(WARNING) << "VssSocketComm already running";
        return true;
    }

    if (!setupServerSocket()) {
        LOG(ERROR) << "Failed to setup server socket";
        return false;
    }

    mRunning = true;
    mReadThread = std::thread(&VssSocketComm::readLoop, this);

    LOG(INFO) << "VssSocketComm started on port " << mPort;
    return true;
}

void VssSocketComm::stop() {
    if (!mRunning.load()) {
        return;
    }

    LOG(INFO) << "Stopping VssSocketComm...";
    mRunning = false;
    
    closeSocket();
    
    if (mReadThread.joinable()) {
        mReadThread.join();
    }
    
    LOG(INFO) << "VssSocketComm stopped";
}

bool VssSocketComm::isRunning() const {
    return mRunning.load();
}

bool VssSocketComm::setupServerSocket() {
    mServerSocket = socket(AF_INET, SOCK_STREAM, 0);
    if (mServerSocket < 0) {
        LOG(ERROR) << "Failed to create socket: " << strerror(errno);
        return false;
    }

    // Set socket options
    int opt = 1;
    if (setsockopt(mServerSocket, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt)) < 0) {
        LOG(ERROR) << "Failed to set socket options: " << strerror(errno);
        closeSocket();
        return false;
    }

    // Set socket timeout
    struct timeval timeout;
    timeout.tv_sec = SOCKET_TIMEOUT_SEC;
    timeout.tv_usec = 0;
    setsockopt(mServerSocket, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout));

    // Bind socket
    struct sockaddr_in address;
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = INADDR_ANY;
    address.sin_port = htons(mPort);

    if (bind(mServerSocket, (struct sockaddr*)&address, sizeof(address)) < 0) {
        LOG(ERROR) << "Failed to bind socket to port " << mPort << ": " << strerror(errno);
        closeSocket();
        return false;
    }

    // Listen for connections
    if (listen(mServerSocket, 1) < 0) {
        LOG(ERROR) << "Failed to listen on socket: " << strerror(errno);
        closeSocket();
        return false;
    }

    LOG(INFO) << "Server socket setup complete, listening on port " << mPort;
    return true;
}

void VssSocketComm::closeSocket() {
    if (mClientSocket >= 0) {
        close(mClientSocket);
        mClientSocket = -1;
        mHasActiveConnection = false;
    }
    
    if (mServerSocket >= 0) {
        close(mServerSocket);
        mServerSocket = -1;
    }
}

void VssSocketComm::readLoop() {
    LOG(INFO) << "VSS socket read loop started";
    
    while (mRunning.load()) {
        if (!mHasActiveConnection.load() && !acceptConnection()) {
            // No connection, wait a bit before retrying
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
            continue;
        }

        std::string message = readMessage();
        if (!message.empty()) {
            processMessage(message);
        } else if (!mHasActiveConnection.load()) {
            // Connection lost, try to accept new one
            LOG(INFO) << "Connection lost, waiting for new connection...";
        }
    }
    
    LOG(INFO) << "VSS socket read loop ended";
}

bool VssSocketComm::acceptConnection() {
    if (mServerSocket < 0) {
        return false;
    }

    struct sockaddr_in client_addr;
    socklen_t client_len = sizeof(client_addr);
    
    mClientSocket = accept(mServerSocket, (struct sockaddr*)&client_addr, &client_len);
    
    if (mClientSocket < 0) {
        if (errno == EWOULDBLOCK || errno == EAGAIN) {
            // Timeout, which is normal
            return false;
        }
        LOG(ERROR) << "Failed to accept connection: " << strerror(errno);
        return false;
    }

    // Set client socket timeout
    struct timeval timeout;
    timeout.tv_sec = SOCKET_TIMEOUT_SEC;
    timeout.tv_usec = 0;
    setsockopt(mClientSocket, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout));

    mHasActiveConnection = true;
    LOG(INFO) << "Accepted VSS client connection";
    return true;
}

std::string VssSocketComm::readMessage() {
    if (mClientSocket < 0 || !mHasActiveConnection.load()) {
        return "";
    }

    char buffer[BUFFER_SIZE];
    std::string message;
    
    while (mRunning.load() && mHasActiveConnection.load()) {
        ssize_t bytes_read = recv(mClientSocket, buffer, BUFFER_SIZE - 1, 0);
        
        if (bytes_read > 0) {
            buffer[bytes_read] = '\0';
            message += buffer;
            
            // Look for newline to determine end of message
            size_t newline_pos = message.find('\n');
            if (newline_pos != std::string::npos) {
                std::string complete_message = message.substr(0, newline_pos);
                message = message.substr(newline_pos + 1);
                
                // Trim whitespace
                complete_message.erase(complete_message.find_last_not_of(" \t\r\n") + 1);
                
                if (!complete_message.empty()) {
                    LOG(VERBOSE) << "Received VSS message: " << complete_message;
                    return complete_message;
                }
            }
        } else if (bytes_read == 0) {
            // Client disconnected
            LOG(INFO) << "VSS client disconnected";
            mHasActiveConnection = false;
            close(mClientSocket);
            mClientSocket = -1;
            break;
        } else {
            // Error or timeout
            if (errno == EWOULDBLOCK || errno == EAGAIN) {
                // Timeout, continue reading
                continue;
            } else {
                LOG(ERROR) << "Socket read error: " << strerror(errno);
                mHasActiveConnection = false;
                close(mClientSocket);
                mClientSocket = -1;
                break;
            }
        }
    }
    
    return "";
}

}  // namespace impl
}  // namespace V2_0
}  // namespace vehicle
}  // namespace automotive
}  // namespace hardware
}  // namespace android
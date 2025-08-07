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

#include <android/hardware/automotive/vehicle/2.0/IVehicle.h>
#include <string>
#include <vector>

namespace android {
namespace hardware {
namespace automotive {
namespace vehicle {
namespace V2_0 {
namespace impl {

using ::android::hardware::automotive::vehicle::V2_0::VehiclePropValue;

/**
 * ConverterUtils provides reusable helper functions for VSS to VHAL conversion.
 * This utility class keeps the AndroidVssConverter clean and focused on its 
 * primary job of mapping VSS data while handling common tasks like:
 * 
 * 1. String parsing and validation
 * 2. Data type conversions 
 * 3. VehiclePropValue structure initialization and manipulation
 * 4. Unit conversions and value clamping
 */
class ConverterUtils {
public:
    /**
     * Initialize a VehiclePropValue structure with basic properties.
     * @param propValue VehiclePropValue to initialize
     * @param propertyId VHAL property ID
     * @param areaId Area ID (default: 0 for global properties)
     */
    static void initializeProp(VehiclePropValue& propValue, int32_t propertyId, int32_t areaId = 0);

    // String parsing and validation functions
    
    /**
     * Check if a string represents a valid float number.
     * @param str String to check
     * @return true if string represents a float, false otherwise
     */
    static bool isFloatString(const std::string& str);
    
    /**
     * Check if a string represents a valid integer number.
     * @param str String to check
     * @return true if string represents an integer, false otherwise
     */
    static bool isIntString(const std::string& str);
    
    /**
     * Check if a string represents a boolean value.
     * @param str String to check
     * @return true if string represents a boolean, false otherwise
     */
    static bool isBoolString(const std::string& str);

    // String to data type conversion functions
    
    /**
     * Convert string to float with error handling.
     * @param str String to convert
     * @return Float value
     * @throws std::invalid_argument if conversion fails
     */
    static float stringToFloat(const std::string& str);
    
    /**
     * Convert string to int32_t with error handling.
     * @param str String to convert
     * @return Int32 value
     * @throws std::invalid_argument if conversion fails
     */
    static int32_t stringToInt32(const std::string& str);
    
    /**
     * Convert string to int64_t with error handling.
     * @param str String to convert
     * @return Int64 value
     * @throws std::invalid_argument if conversion fails
     */
    static int64_t stringToInt64(const std::string& str);
    
    /**
     * Convert string to boolean.
     * Accepts: "true"/"false", "1"/"0", "yes"/"no", "on"/"off" (case-insensitive)
     * @param str String to convert
     * @return Boolean value
     * @throws std::invalid_argument if conversion fails
     */
    static bool stringToBool(const std::string& str);
    
    /**
     * Convert hex string to byte array.
     * @param hexStr Hex string (e.g., "1A2B3C")
     * @return Vector of bytes
     * @throws std::invalid_argument if conversion fails
     */
    static std::vector<uint8_t> hexStringToBytes(const std::string& hexStr);

    // VehiclePropValue manipulation functions
    
    /**
     * Set float value in VehiclePropValue.
     * @param propValue VehiclePropValue to modify
     * @param value Float value to set
     */
    static void setFloatValue(VehiclePropValue& propValue, float value);
    
    /**
     * Set int32 value in VehiclePropValue.
     * @param propValue VehiclePropValue to modify
     * @param value Int32 value to set
     */
    static void setInt32Value(VehiclePropValue& propValue, int32_t value);
    
    /**
     * Set int64 value in VehiclePropValue.
     * @param propValue VehiclePropValue to modify
     * @param value Int64 value to set
     */
    static void setInt64Value(VehiclePropValue& propValue, int64_t value);
    
    /**
     * Set boolean value in VehiclePropValue.
     * @param propValue VehiclePropValue to modify
     * @param value Boolean value to set
     */
    static void setBoolValue(VehiclePropValue& propValue, bool value);
    
    /**
     * Set string value in VehiclePropValue.
     * @param propValue VehiclePropValue to modify
     * @param value String value to set
     */
    static void setStringValue(VehiclePropValue& propValue, const std::string& value);
    
    /**
     * Set bytes value in VehiclePropValue.
     * @param propValue VehiclePropValue to modify
     * @param value Bytes vector to set
     */
    static void setBytesValue(VehiclePropValue& propValue, const std::vector<uint8_t>& value);

    // Utility functions for value processing
    
    /**
     * Clamp a float value between min and max bounds.
     * @param value Value to clamp
     * @param minVal Minimum allowed value
     * @param maxVal Maximum allowed value
     * @return Clamped value
     */
    static float clampFloat(float value, float minVal, float maxVal);
    
    /**
     * Clamp an int32 value between min and max bounds.
     * @param value Value to clamp
     * @param minVal Minimum allowed value
     * @param maxVal Maximum allowed value
     * @return Clamped value
     */
    static int32_t clampInt32(int32_t value, int32_t minVal, int32_t maxVal);
    
    /**
     * Apply linear scaling to a float value (value * multiplier + offset).
     * @param value Input value
     * @param multiplier Scaling multiplier
     * @param offset Offset to add
     * @return Scaled value
     */
    static float applyLinearScaling(float value, float multiplier, float offset);

private:
    // Helper functions
    static std::string toLower(const std::string& str);
    static std::string trim(const std::string& str);
    static bool isValidHexChar(char c);
    static uint8_t hexCharToByte(char c);
};

}  // namespace impl
}  // namespace V2_0
}  // namespace vehicle
}  // namespace automotive
}  // namespace hardware
}  // namespace android
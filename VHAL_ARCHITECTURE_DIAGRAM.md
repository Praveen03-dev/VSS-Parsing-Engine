# 🏗️ VHAL Architecture - File Interaction Diagram

## 📊 **System Architecture Overview**

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           🚗 ANDROID AUTOMOTIVE VHAL SYSTEM                     │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│   🛡️ FRAMEWORK     │    │   📱 ANDROID APPS   │    │  🔧 EXTERNAL TOOLS │
│                     │    │                     │    │                     │
│ • CarService        │    │ • Navigation App    │    │ • VSS Data Provider │
│ • VehicleManager    │    │ • Climate App       │    │ • Test Scripts      │
│ • Property API      │    │ • Dashboard App     │    │ • Simulators        │
└─────────┬───────────┘    └─────────┬───────────┘    └─────────┬───────────┘
          │                          │                          │
          │ HIDL Interface           │ HIDL Interface           │ TCP Socket
          │ (get/set/subscribe)      │ (get/set/subscribe)      │ Port 33445
          ▼                          ▼                          ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            📘 HIDL INTERFACE LAYER                             │
│                                                                                 │
│  IVehicle.hal          IVehicleCallback.hal         types.hal                 │
│  ┌─────────────────┐   ┌─────────────────┐         ┌─────────────────┐        │
│  │ • get()         │   │ • onPropertyEvent()│       │ • VehicleProperty│        │
│  │ • set()         │   │ • onPropertySetError() │   │ • Property IDs   │        │
│  │ • subscribe()   │   │                 │         │ • Data Types     │        │
│  │ • getAllConfigs()│  │                 │         │ • 7,074 Properties│       │
│  └─────────────────┘   └─────────────────┘         └─────────────────┘        │
└─────────────────────────┬───────────────────────────────────────────────────────┘
                          │
                          │ Implements
                          ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         🚀 MAIN SERVICE ENTRY POINT                            │
│                                                                                 │
│                            VehicleService.cpp                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │ main() {                                                                │    │
│  │   configureRpcThreadpool(4);                                          │    │
│  │   auto hal = new DefaultVehicleHal();                                 │    │
│  │   auto service = new VehicleHalManager(hal);                          │    │
│  │   service->registerAsService();                                       │    │
│  │   joinRpcThreadpool();                                                │    │
│  │ }                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────┬───────────────────────────────────────────────────────┘
                          │
                          │ Creates & Manages
                          ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        🏛️ CORE VHAL IMPLEMENTATION                             │
│                                                                                 │
│                    DefaultVehicleHal.h/.cpp                                    │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │ • get(property) → reads sensor/stored value                            │    │
│  │ • set(property) → writes to actuator/store                             │    │
│  │ • subscribe(property, rate) → manages subscriptions                    │    │
│  │ • Coordinates with VssVehicleEmulator                                  │    │
│  │ • Contains 7,074 property-specific methods                             │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                 │
│  Uses: DefaultConfig.h (property metadata)                                     │
│        PropertyUtils.cpp (value manipulation)                                  │
│        SubscriptionManager.h (subscription handling)                           │
└─────────────────────────┬───────────────────────────────────────────────────────┘
                          │
                          │ Integrates with
                          ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      ⭐ VSS CONVERTER SYSTEM (THE MAGIC!)                      │
│                                                                                 │
│                      VssVehicleEmulator.h/.cpp                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │ class VssVehicleEmulator : public VehicleEmulator,                     │    │
│  │                           public VssMessageProcessor {                  │    │
│  │   void processVssMessage("Vehicle.Speed=120.5") {                     │    │
│  │     parseMessage(msg, path, value);                                    │    │
│  │     mVssConverter->convertVssToVhal(path, value, propValue);          │    │
│  │     updateVhalProperty(propValue);                                     │    │
│  │   }                                                                     │    │
│  │ }                                                                       │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
└─────────────┬───────────────────────────┬───────────────────────────────────────┘
              │                           │
              │ Uses                      │ Uses
              ▼                           ▼
┌─────────────────────────────┐  ┌─────────────────────────────────────────┐
│    📡 COMMUNICATION         │  │     🔄 DYNAMIC CONVERTER               │
│                             │  │                                         │
│  VssSocketComm.h/.cpp       │  │  AndroidVssConverter.h/.cpp             │
│  ┌─────────────────────────┐ │  │  ┌─────────────────────────────────────┐ │
│  │ • Listen on port 33445  │ │  │  │ • 7,074 conversion functions       │ │
│  │ • Accept TCP connections│ │  │  │ • Runtime mapping table             │ │
│  │ • Read VSS messages     │ │  │  │ • convertVehicle_Speed()            │ │
│  │ • Thread-safe operation │ │  │  │ • convertVehicle_Engine_RPM()       │ │
│  │ • Auto-reconnection     │ │  │  │ • Unit conversion & validation      │ │
│  └─────────────────────────┘ │  │  └─────────────────────────────────────┘ │
│                             │  │                                         │
│  VssCommConn.h/.cpp         │  │  Uses: ConverterUtils.h/.cpp            │
│  (Abstract base class)      │  │  ┌─────────────────────────────────────┐ │
│                             │  │  │ • stringToFloat()                   │ │
│                             │  │  │ • setFloatValue()                   │ │
│                             │  │  │ • clampValue()                      │ │
│                             │  │  │ • initializeProp()                  │ │
│                             │  │  └─────────────────────────────────────┘ │
└─────────────────────────────┘  └─────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                          📊 CONFIGURATION & METADATA                           │
│                                                                                 │
│  DefaultConfig.h                PropertyUtils.h/.cpp                           │
│  ┌─────────────────────────────┐ ┌─────────────────────────────────────────┐   │
│  │ • 7,074 property configs    │ │ • Property creation utilities           │   │
│  │ • Access permissions        │ │ • Value validation                      │   │
│  │ • Change modes              │ │ • Serialization helpers                 │   │
│  │ • Initial values            │ │                                         │   │
│  │ • Valid ranges              │ └─────────────────────────────────────────┘   │
│  └─────────────────────────────┘                                               │
│                                                                                 │
│  SubscriptionManager.h                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │ • Manages property subscriptions                                        │   │
│  │ • Sample rate control                                                   │   │
│  │ • Threaded update generation                                            │   │
│  │ • Notification callbacks                                                │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                            ⚙️ BUILD & SERVICE CONFIG                           │
│                                                                                 │
│  Android.bp                     service.rc                  service.xml        │
│  ┌─────────────────────┐        ┌─────────────────────┐    ┌─────────────────┐ │
│  │ • Build rules       │        │ • Service startup   │    │ • Service       │ │
│  │ • Dependencies      │        │ • User permissions  │    │   manifest      │ │
│  │ • Compiler flags    │        │ • Process control   │    │ • Interface     │ │
│  │ • Link libraries    │        │                     │    │   declaration   │ │
│  └─────────────────────┘        └─────────────────────┘    └─────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 🔄 **Data Flow Example: VSS Message Processing**

```
1. External Tool                    2. Socket Layer                3. Message Parser
   │                                  │                             │
   │ "Vehicle.Speed=120.5"            │ VssSocketComm              │ VssVehicleEmulator
   │ ──TCP──► Port 33445              │ ────reads────►             │ ────parses────►
   │                                  │                             │
   │                                  │                             ▼
   │                                  │                    ┌─────────────────────┐
   │                                  │                    │ path="Vehicle.Speed" │
   │                                  │                    │ value="120.5"       │
   │                                  │                    └─────────────────────┘

4. Dynamic Converter               5. Utils & Validation           6. VHAL Update
   │                                │                               │
   │ AndroidVssConverter           │ ConverterUtils                │ DefaultVehicleHal
   │ ────converts────►             │ ────validates────►            │ ────updates────►
   │                               │                               │
   ▼                               ▼                               ▼
┌─────────────────────┐         ┌─────────────────────┐        ┌─────────────────────┐
│ convertVehicle_Speed│         │ stringToFloat(120.5)│        │ Property Store      │
│ Property: 0x11600207│         │ * 3.6 = 433.8 km/h │        │ VEHICLE_SPEED =     │
│ Type: FLOAT         │         │ clamp(0, 300) = 300│        │ 300.0 km/h          │
└─────────────────────┘         └─────────────────────┘        └─────────────────────┘

7. Framework Notification        8. App Response
   │                              │
   │ SubscriptionManager          │ Android App
   │ ────notifies────►            │ ────receives────►
   │                              │
   ▼                              ▼
┌─────────────────────┐        ┌─────────────────────┐
│ onPropertyEvent()   │        │ UI Update:          │
│ VEHICLE_SPEED       │        │ "Speed: 300 km/h"  │
│ value=300.0         │        │                     │
└─────────────────────┘        └─────────────────────┘
```

## 🎯 **Key Architectural Principles**

### 🔧 **Separation of Concerns**
- **Interface Layer**: HIDL definitions (types.hal, IVehicle.hal)
- **Service Layer**: Entry point and lifecycle (VehicleService.cpp)
- **Implementation Layer**: Core logic (DefaultVehicleHal.cpp)
- **Conversion Layer**: VSS processing (VssVehicleEmulator, AndroidVssConverter)
- **Communication Layer**: External data (VssSocketComm, VssCommConn)
- **Utility Layer**: Helper functions (ConverterUtils, PropertyUtils)

### 🔄 **Plugin Architecture**
- **VssCommConn** is abstract → easily swap socket for CAN/UART/etc.
- **AndroidVssConverter** is generated → easily add new VSS signals
- **Mock hardware** layer → easily add real sensor integration

### ⚡ **Performance Optimizations**
- **Pre-compiled conversion functions** → no runtime parsing of rules
- **Hash map lookups** → O(1) VSS path to converter function mapping
- **Threaded communication** → non-blocking message processing
- **Efficient property store** → minimal memory overhead

This architecture enables your system to handle **7,074 VSS signals** with **real-time performance** and **zero configuration overhead**! 🚀

# Smart Buoy System for Optical Detection and AI-Based Classification of Microplastics in Marine Environments

## Overview

Marine plastic pollution is a growing environmental concern, with microplastics posing significant risks to aquatic ecosystems. This project focuses on developing a smart buoy system that uses optical sensing, embedded systems, and sensor integration to support the detection and monitoring of microplastics in marine environments.

The system uses an array of photodiodes to acquire optical measurements. An STM32 microcontroller processes the acquisition workflow and transmits the collected data to an ESP32. The ESP32 integrates environmental and motion sensor readings and transfers the data wirelessly to a Python-based application for real-time visualization and data logging.

This repository contains the firmware and software developed for the project's embedded data acquisition, sensor integration, communication, and visualization workflow.

## Key Features

- Optical data acquisition using an array of BPW34 photodiodes.
- Analog signal selection using the CD4067BE 16-channel multiplexer.
- Signal conditioning using the TLC272 operational amplifier.
- STM32-based embedded firmware for photodiode data acquisition.
- UART communication between the STM32 and ESP32.
- Integration of temperature, pressure, motion, and GPS sensors.
- Wireless data transmission from the ESP32 to a Python application using UDP over Wi-Fi.
- Real-time visualization of photodiode readings and sensor measurements.
- Heatmap visualization of the photodiode array.
- Continuous data logging to CSV files for further analysis.

## System Architecture

The system follows a modular architecture in which optical data acquisition, sensor integration, wireless communication, and visualization are handled by different components.

```text
                 Optical Sensing Unit
                         |
                  BPW34 Photodiodes
                         |
                  CD4067BE Multiplexer
                         |
                  TLC272 Signal Conditioning
                         |
                         v
                  STM32 Blue Pill
                  (STM32F103C8T6)
                         |
                    UART Communication
                         |
                         v
                   ESP32-WROOM-32
                         |
          +--------------+--------------+
          |              |              |
          v              v              v
       BMP280         MPU6050         NEO-6M
    Temperature/     Accelerometer/      GPS
      Pressure        Gyroscope
          |              |              |
          +--------------+--------------+
                         |
                  Wi-Fi / UDP
                         |
                         v
                 Python Application
                       (app.py)
                         |
          +--------------+--------------+
          |              |              |
          v              v              v
     Live Sensor     Photodiode       CSV Data
     Readings         Heatmap          Logging
```

## Hardware Components

| Component | Purpose |
|---|---|
| STM32 Blue Pill (STM32F103C8T6) | Embedded control and photodiode data acquisition |
| ESP32-WROOM-32 | Sensor integration and wireless data transmission |
| BPW34 Photodiodes | Optical sensing |
| CD4067BE | 16-channel analog multiplexer for selecting photodiode signals |
| TLC272 | Analog signal conditioning |
| BMP280 | Temperature and pressure measurements |
| MPU6050 | Accelerometer and gyroscope measurements |
| NEO-6M GPS | GPS positioning data |

## Software and Development Tools

| Software / Tool | Purpose |
|---|---|
| STM32CubeIDE | STM32 firmware development and project configuration |
| Embedded C | Microcontroller firmware development |
| Python | Data reception, visualization, and logging |
| UART | Communication between the STM32 and ESP32 |
| Wi-Fi and UDP | Wireless transfer of data from the ESP32 to the Python application |
| CSV | Storage of acquired measurements for further analysis |

## Repository Structure

The repository contains separate firmware projects for testing, photodiode acquisition, UART communication, and integrated system operation.

```text
Major-Project-/
│
├── MajorProject/
│   └── Integrated STM32 firmware and project files
│
├── mySTMBlinky/
│   └── Basic STM32 LED blink test
│
├── photodiode_UART_ESP/
│   └── Photodiode acquisition and STM32-to-ESP32
│       communication firmware
│
└── photodiode_aquisition/
    └── Photodiode acquisition firmware
```

The Python application (`app.py`) is used for receiving and visualizing the transmitted data. Its location in the repository may depend on the final project directory organization.

### Directory Descriptions

**`mySTMBlinky/`**

Contains a basic LED blinking project for testing the STM32 Blue Pill board and verifying the initial firmware development environment.

**`photodiode_aquisition/`**

Contains firmware associated with photodiode data acquisition.

**`photodiode_UART_ESP/`**

Contains firmware for photodiode data acquisition and UART communication between the STM32 and ESP32. The ESP32 integrates readings from the BMP280, MPU6050, and NEO-6M GPS before transmitting the collected data to the Python application over Wi-Fi using UDP.

**`MajorProject/`**

Contains the integrated STM32 firmware developed for the major project. The firmware handles photodiode acquisition and transmits the collected data to the ESP32 for subsequent wireless transfer and visualization.

## Data Acquisition and Communication

### 1. Optical Data Acquisition

The photodiode array captures optical measurements. The CD4067BE multiplexer enables the selection of individual photodiode channels, while the TLC272 supports analog signal conditioning.

The STM32 microcontroller manages the photodiode acquisition process and prepares the readings for transmission.

### 2. STM32–ESP32 Communication

The STM32 transmits the acquired photodiode data to the ESP32 through UART communication.

The ESP32 receives the optical measurements and integrates them with the environmental, motion, and GPS readings obtained from the connected sensors.

### 3. Wireless Data Transmission

The ESP32 sends the collected data to the Python application through Wi-Fi using the UDP protocol.

This architecture separates low-level data acquisition from wireless communication and application-level visualization.

### 4. Real-Time Visualization

The Python application displays incoming photodiode readings and sensor measurements in real time. The photodiode array is represented as a heatmap to facilitate visual interpretation of the optical measurements.

### 5. Data Logging

The application continuously records acquired measurements in CSV format. The logged data can be downloaded and used for subsequent analysis, experimentation, and model development.

## Running the Python Application

The Python application is responsible for receiving data from the ESP32, displaying live measurements, generating the photodiode heatmap, and logging data.

To run the application:

1. Clone or download this repository.
2. Locate the Python application file (`app.py`) and review any required dependencies.
3. Install the required Python packages based on the project's implementation.
4. Configure the application and ESP32 to use the appropriate network settings.
5. Ensure that the ESP32 is transmitting data to the IP address and UDP port expected by the application.
6. Run the Python application.

```bash
python3 app.py
```

The application should be run in an environment where it can receive UDP packets from the ESP32.

*Note: The exact Python dependencies, network configuration, and UDP port depend on the implementation in the source files.*

## Firmware Development

The STM32 firmware was developed using STM32CubeIDE and Embedded C. The repository includes separate projects for basic board testing, photodiode acquisition, UART communication, and integrated system operation.

The firmware modules support the project's embedded data acquisition and communication workflow, allowing the optical measurements to be transferred to the ESP32 for integration with additional sensor readings.

## Optical Detection and Data Analysis

The optical sensing subsystem uses photodiodes to obtain measurements associated with the optical detection process. These readings are collected through the embedded acquisition system and made available to the Python application.

The real-time heatmap provides a visual representation of the photodiode array, while CSV logging preserves the acquired measurements for offline processing and further analysis.

The broader project also explores AI-based classification of microplastics. The availability of classification functionality depends on the implementation of the corresponding processing and model components.

## Future Scope

Potential directions for further development include:

- Integrating and validating machine-learning models for microplastic classification.
- Improving optical measurement calibration and repeatability.
- Enhancing noise filtering and signal-processing techniques.
- Expanding real-time visualization and data analysis capabilities.
- Evaluating system performance under different environmental conditions.
- Extending data collection to support further experimental validation.

Firmware and software designed and developed by Ameya Joshi.

## Project Team

The project was developed collaboratively by:

- Prathamesh Mane
- Tanvi Wani
- Ameya Joshi
- Tanmay Wani
- Aniruddh Nalli

## Acknowledgements

The project was developed at Bharatiya Vidya Bhavan's Sardar Patel Institute of Technology (SPIT), Mumbai, under the guidance of Dr. Reena Sonkusare, Head of the Department of Electronics and Telecommunication Engineering, and Dr. Satyanarayana Bheesette.

Department of Electronics and Telecommunication Engineering  
Bharatiya Vidya Bhavan's Sardar Patel Institute of Technology, Mumbai  
Academic Batch: 2026

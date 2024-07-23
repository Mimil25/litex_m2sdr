#!/usr/bin/env python3

# This file is part of LiteX-M2SDR.
#
# Copyright (c) 2024 Enjoy-Digital <enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause

import re
import argparse
import subprocess

# Test Constants -----------------------------------------------------------------------------------

# VCC Constants.
VCC_INT_NOMINAL  = 1.00 # V.
VCC_AUX_NOMINAL  = 1.80 # V.
VCC_BRAM_NOMINAL = 1.00 # V.
VCC_MARGIN       =   10 # %.

# FPGA/PCIe Constants.
FPGA_PCIE_VENDOR_ID          = "0x10ee"
FPGA_PCIE_DEVICE_IDS         = ["0x7021", "0x7022", "0x7024"]
FPGA_PCIE_SPEED_NOMINAL      = "5.0 GT/s PCIe"
FPGA_PCIE_LINK_WIDTH_NOMINAL = {"m2" : "4", "baseboard" : "1"}

# AD9361 Constants.
AD9361_PRODUCT_ID = "000a"

# DMA Loopback Test Constants.
DMA_LOOPBACK_TEST_DURATION   = 2                              # Seconds.
DMA_LOOPBACK_SPEED_THRESHOLD = {"m2" : 10, "baseboard" : 2.5} # Gbps.

# RFIC Test Constants.
RFIC_SAMPLERATES = [
    2.5e6,
    5.0e6,
    10.0e6,
    20.0e6,
    30.72e6,
    61.44e6,
]

# RFIC Loopback Test Constants.
RFIC_LOOPBACK_TEST_DURATION   = 2   # Seconds.
RFIC_LOOPBACK_SPEED_THRESHOLD = 1.4 # Gbps.

# VCXO Constants.
VCXO_PPM_THRESHOLD = 20.0 # PPM.

# Color Constants ----------------------------------------------------------------------------------

ANSI_COLOR_RED    = "\x1b[31m"
ANSI_COLOR_GREEN  = "\x1b[32m"
ANSI_COLOR_YELLOW = "\x1b[33m"
ANSI_COLOR_BLUE   = "\x1b[34m"
ANSI_COLOR_RESET  = "\x1b[0m"

# Helpers ------------------------------------------------------------------------------------------

def print_pass():
    print(f"{ANSI_COLOR_GREEN}[PASS]{ANSI_COLOR_RESET}")

def print_fail():
    print(f"{ANSI_COLOR_RED}[FAIL]{ANSI_COLOR_RESET}")

def print_result(condition):
    if condition:
        print_pass()
    else:
        print_fail()
    return not condition

def within_margin(value, nominal, margin=10):
    return nominal * (1 - margin/100) <= value <= nominal * (1 + margin/100)

def get_pcie_device_id(vendor, device):
    try:
        lspci_output = subprocess.check_output(["lspci", "-d", f"{vendor}:{device}"]).decode()
        device_id = lspci_output.split()[0]
        return device_id
    except:
        return None

def get_board_variant():
    result = subprocess.run("cd user && ./m2sdr_util info", shell=True, capture_output=True, text=True)
    output = result.stdout

    # Get Variant.
    for variant in ["m2", "baseboard"]:
        if f"{variant} variant" in output:
            return variant
    return None

def verify_pcie_speed(device_id):
    try:
        device_path = f"/sys/bus/pci/devices/0000:{device_id}"
        current_link_speed = subprocess.check_output(f"cat {device_path}/current_link_speed", shell=True).decode().strip()
        current_link_width = subprocess.check_output(f"cat {device_path}/current_link_width", shell=True).decode().strip()

        board_variant = get_board_variant()

        speed_check = (current_link_speed == FPGA_PCIE_SPEED_NOMINAL)
        width_check = (current_link_width == FPGA_PCIE_LINK_WIDTH_NOMINAL[board_variant])

        return current_link_speed, current_link_width, speed_check and width_check
    except:
        return None, None, False

# PCIe Device Test ---------------------------------------------------------------------------------

def pcie_device_autotest():
    print("PCIe Device Autotest...", end="")

    errors = 1
    device_ids = [get_pcie_device_id(FPGA_PCIE_VENDOR_ID, device_id) for device_id in FPGA_PCIE_DEVICE_IDS]
    for device_id in device_ids:
        if device_id:
            print(f"\n\tChecking PCIe Device {device_id}: ", end="")
            device_present = device_id is not None
            errors += print_result(device_present)
            if device_present:
                print(f"\tVerifying PCIe speed for {device_id}: ", end="")
                current_link_speed, current_link_width, speed_check = verify_pcie_speed(device_id)
                print(f"[{ANSI_COLOR_BLUE}{current_link_speed} x{current_link_width}{ANSI_COLOR_RESET}] ", end="")
                return print_result(speed_check)
    print_fail()
    return errors

# M2SDR Util Test ----------------------------------------------------------------------------------

def m2sdr_util_info_autotest():
    print("M2SDR Util Info Autotest...")
    result = subprocess.run("cd user && ./m2sdr_util info", shell=True, capture_output=True, text=True)
    output = result.stdout

    # Check for LiteX-M2SDR presence in identifier.
    print("\tChecking LiteX-M2SDR identifier: ", end="")
    if print_result("LiteX-M2SDR" in output):
        return 1

    # Extract FPGA DNA, temperatures, VCC values, and AD9361 info.
    fpga_dna_match          = re.search(r"FPGA DNA\s*:\s*(0x\w+)", output)
    fpga_temp_match         = re.search(r"FPGA Temperature\s*:\s*([\d.]+) °C", output)
    vcc_int_match           = re.search(r"FPGA VCC-INT\s*:\s*([\d.]+) V", output)
    vcc_aux_match           = re.search(r"FPGA VCC-AUX\s*:\s*([\d.]+) V", output)
    vcc_bram_match          = re.search(r"FPGA VCC-BRAM\s*:\s*([\d.]+) V", output)
    ad9361_product_id_match = re.search(r"AD9361 Product ID\s*:\s*(\w+)", output)
    ad9361_temp_match       = re.search(r"AD9361 Temperature\s*:\s*([\d.]+) °C", output)

    if not (fpga_dna_match and fpga_temp_match and vcc_int_match and vcc_aux_match and vcc_bram_match and ad9361_product_id_match and ad9361_temp_match):
        print("Failed to retrieve necessary information from m2sdr_util info.")
        print_fail()
        return 1

    board_variant     = get_board_variant()
    fpga_dna          = fpga_dna_match.group(1)
    fpga_temp         = float(fpga_temp_match.group(1))
    vcc_int           = float(vcc_int_match.group(1))
    vcc_aux           = float(vcc_aux_match.group(1))
    vcc_bram          = float(vcc_bram_match.group(1))
    ad9361_product_id = ad9361_product_id_match.group(1)
    ad9361_temp       = float(ad9361_temp_match.group(1))

    errors = 0

    # Print Board Variant.
    print(f"\tBoard Variant: \t\t\t[{ANSI_COLOR_BLUE}{board_variant}{ANSI_COLOR_RESET}]")

    # Print FPGA DNA/Temperature and AD9361 Temperature.
    print(f"\tFPGA DNA: \t\t\t[{ANSI_COLOR_BLUE}{fpga_dna}{ANSI_COLOR_RESET}]")
    print(f"\tFPGA Temperature: \t\t[{ANSI_COLOR_BLUE}{fpga_temp} °C{ANSI_COLOR_RESET}]")

    # Print/Verify VCC values.
    print(f"\tChecking VCCINT: \t\t[{ANSI_COLOR_BLUE}{vcc_int} V{ANSI_COLOR_RESET}] ", end="")
    errors += print_result(within_margin(vcc_int, VCC_INT_NOMINAL, VCC_MARGIN))
    print(f"\tChecking VCCAUX: \t\t[{ANSI_COLOR_BLUE}{vcc_aux} V{ANSI_COLOR_RESET}] ", end="")
    errors += print_result(within_margin(vcc_aux, VCC_AUX_NOMINAL, VCC_MARGIN))
    print(f"\tChecking VCCBRAM: \t\t[{ANSI_COLOR_BLUE}{vcc_bram} V{ANSI_COLOR_RESET}] ", end="")
    errors += print_result(within_margin(vcc_bram, VCC_BRAM_NOMINAL, VCC_MARGIN))

    # Print/Verify AD9361 Product ID/Temperature.
    print(f"\tChecking AD9361 Product ID: \t[{ANSI_COLOR_BLUE}{ad9361_product_id}{ANSI_COLOR_RESET}] ", end="")
    errors += print_result(ad9361_product_id == AD9361_PRODUCT_ID)
    print(f"\tAD9361 Temperature: \t\t[{ANSI_COLOR_BLUE}{ad9361_temp} °C{ANSI_COLOR_RESET}]")

    return errors

# M2SDR Util VCXO Test ----------------------------------------------------------------------------------

def m2sdr_util_vcxo_autotest():
    print("M2SDR Util VCXO Test...")

    log = subprocess.run(f"cd user && ./m2sdr_util vcxo_test", shell=True, capture_output=True, text=True)

    # Parse the variation in Hz and PPM.
    hz_variation_match  = re.search(r"Hz Variation from Nominal \(50% PWM\): -?\s*([\d.]+)\s*Hz\s*/\s*\+\s*([\d.]+)\s*Hz", log.stdout)
    ppm_variation_match = re.search(r"PPM Variation from Nominal \(50% PWM\): -?\s*([\d.]+)\s*PPM\s*/\s*\+\s*([\d.]+)\s*PPM", log.stdout)

    if not (hz_variation_match and ppm_variation_match):
        print("Failed to retrieve necessary information from vcxo_test.")
        print_fail()
        return 1

    hz_variation_min  = float(hz_variation_match.group(1))
    hz_variation_max  = float(hz_variation_match.group(2))
    ppm_variation_min = float(ppm_variation_match.group(1))
    ppm_variation_max = float(ppm_variation_match.group(2))

    errors = 0

    # Print Hz variation.
    print(f"\tHz Variation from Nominal (50% PWM): -[{ANSI_COLOR_BLUE}{hz_variation_min:.2f} Hz{ANSI_COLOR_RESET}] / +[{ANSI_COLOR_BLUE}{hz_variation_max:.2f} Hz{ANSI_COLOR_RESET}]")

    # Print/Verify PPM variation.
    print(f"\tPPM Variation from Nominal (50% PWM): -[{ANSI_COLOR_BLUE}{ppm_variation_min:.2f} PPM{ANSI_COLOR_RESET}] / +[{ANSI_COLOR_BLUE}{ppm_variation_max:.2f} PPM{ANSI_COLOR_RESET}] ", end="")
    ppm_condition = ppm_variation_min >= VCXO_PPM_THRESHOLD and ppm_variation_max >= VCXO_PPM_THRESHOLD
    errors += print_result(ppm_condition)

    return errors

# M2SDR RF Test ------------------------------------------------------------------------------------

def m2sdr_rf_autotest():
    print("M2SDR RF Autotest...")
    errors = 0
    for samplerate in RFIC_SAMPLERATES:
        print(f"\tRF Init @ {samplerate/1e6:3.2f}MSPS...", end="")
        log = subprocess.run(f"cd user && ./m2sdr_rf -samplerate={samplerate}", shell=True, capture_output=True, text=True)
        errors += print_result("AD936x Rev 2 successfully initialized" in log.stdout)
    return errors

# M2SDR DMA Loopback Test --------------------------------------------------------------------------

def m2sdr_dma_loopback_autotest():
    print("M2SDR DMA Loopback Test...")

    log = subprocess.run(f"cd user && ./m2sdr_util dma_test -t {DMA_LOOPBACK_TEST_DURATION}", shell=True, capture_output=True, text=True)

    errors = 0
    dma_speeds = re.findall(r"^\s*([\d.]+)\s+.*$", log.stdout, re.MULTILINE)
    dma_errors = re.findall(r"^\s*[\d.]+\s+.*\s+(\d+)\s*$", log.stdout, re.MULTILINE)

    total_speed  = 0.0
    total_errors = 0

    board_variant = get_board_variant()

    if dma_speeds and dma_errors:
        for speed, error in zip(dma_speeds, dma_errors):
            speed = float(speed)
            error = int(error)
            total_speed += speed
            total_errors += error
            print(f"\tChecking DMA speed: [{ANSI_COLOR_BLUE}{speed} Gbps{ANSI_COLOR_RESET}] ", end="")
            errors += print_result(speed > DMA_LOOPBACK_SPEED_THRESHOLD[board_variant])
            print(f"\tChecking DMA errors: [{ANSI_COLOR_BLUE}{error}{ANSI_COLOR_RESET}] ", end="")
            errors += print_result(error == 0)

        mean_speed = total_speed / len(dma_speeds)
        print(f"\tMean DMA speed: [{ANSI_COLOR_BLUE}{mean_speed} Gbps{ANSI_COLOR_RESET}]")
        print(f"\tTotal DMA errors: [{ANSI_COLOR_BLUE}{total_errors}{ANSI_COLOR_RESET}]")
    else:
        print_fail()
        errors += 1

    return errors

# M2SDR RFIC Loopback Test -------------------------------------------------------------------------

def m2sdr_rfic_loopback_autotest():
    print("M2SDR RFIC Loopback Test...")

    # Configure RFIC @ 30.72MSPS with internal loopback set.
    log = subprocess.run(f"cd user && ./m2sdr_rf -loopback=1 -samplerate=30.72e6",  shell=True, capture_output=True, text=True)

    # Run RFIC loopback test.
    log = subprocess.run(f"cd user && ./m2sdr_util dma_test -w 12 -e -a -t {RFIC_LOOPBACK_TEST_DURATION}", shell=True, capture_output=True, text=True)

    errors = 0
    dma_speeds = re.findall(r"^\s*([\d.]+)\s+.*$", log.stdout, re.MULTILINE)
    dma_errors = re.findall(r"^\s*[\d.]+\s+.*\s+(\d+)\s*$", log.stdout, re.MULTILINE)

    total_speed  = 0.0
    total_errors = 0

    # Skip initial results (can contains errors).
    dma_speeds = dma_speeds[2:]
    dma_errors = dma_errors[2:]

    if dma_speeds and dma_errors:
        for speed, error in zip(dma_speeds, dma_errors):
            speed = float(speed)
            error = int(error)
            total_speed += speed
            total_errors += error
            print(f"\tChecking DMA speed: [{ANSI_COLOR_BLUE}{speed} Gbps{ANSI_COLOR_RESET}] ", end="")
            errors += print_result(speed > RFIC_LOOPBACK_SPEED_THRESHOLD)
            print(f"\tChecking DMA errors: [{ANSI_COLOR_BLUE}{error}{ANSI_COLOR_RESET}] ", end="")
            errors += print_result(error == 0)

        mean_speed = total_speed / len(dma_speeds)
        print(f"\tMean DMA speed: [{ANSI_COLOR_BLUE}{mean_speed} Gbps{ANSI_COLOR_RESET}]")
        print(f"\tTotal DMA errors: [{ANSI_COLOR_BLUE}{total_errors}{ANSI_COLOR_RESET}]")
    else:
        print_fail()
        errors += 1

    return errors

# Main ---------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="LiteX M2SDR board Autotest.")
    args = parser.parse_args()

    print("\nLITEX M2SDR AUTOTEST\n" + "-"*40)

    errors = 0

    # PCIe Device Autotest.
    errors += pcie_device_autotest()

    # M2SDR Util Info Autotest.
    errors += m2sdr_util_info_autotest()

    # M2SDR Util VCXO Autotest.
    #errors += m2sdr_util_vcxo_autotest()

    # M2SDR RF Autotest.
    errors += m2sdr_rf_autotest()

    # M2SDR DMA Loopback Autotest.
    errors += m2sdr_dma_loopback_autotest()

    # M2SDR RFIC Loopback Autotest.
    errors += m2sdr_rfic_loopback_autotest()

    print("\n" + "-"*40)

    if errors:
        print(f"LITEX M2SDR AUTOTEST [{ANSI_COLOR_RED}FAIL{ANSI_COLOR_RESET}]")
    else:
        print(f"LITEX M2SDR AUTOTEST [{ANSI_COLOR_GREEN}PASS{ANSI_COLOR_RESET}]")

if __name__ == '__main__':
    main()

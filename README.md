### 🚀 Testers wanted:
We are looking for people to test the integration and find out how much money you save.  Please email me at william.murphy@optispark.ai or raise github issues.  Thanks!

# ![logo](https://github.com/Big-Tree/HomeAssistant-OptiSpark/blob/main/logo.png)

Welcome to OPTISPARK, where we aim to enhance your heat pump's performance, enabling it to take advantage of variable electricity prices. By intelligently managing your heat pump, OPTISPARK can help you reduce electricity costs by approximately 20%.



## Key benefits:
- **Cost Reduction:** Reduce your electricity cost by roughly 20%
- **Temperature Maintenance:** Ensure your home's temperature remains in a comfortable range
- **Additional Savings:** Save more by increasing the temperature range, automatically lowering the house temperature during peak electricity prices

Find out how much you could save for your area: [OPTISPARK.ai/demo](https://optispark.ai/demo/)

# How does it work?
If you are on Octopus's agile electricity tariff, prices vary throughout the day.  Our algorithm adapts to your home's thermal profile and adjusts the heat pump to use more electricity during cheaper periods, and less during expensive periods.

To save more money you can increase the temperature range, this allows the home to drop in temperature during an expensive period.

# Install
Install HACS if not already installed: [hacs.xyz/docs/setup/download/](https://hacs.xyz/docs/setup/download/)
## HACS
### Add the custom integration to HACS

1. HACS -> Integrations -> ⚙️Options -> Custom repositories
2. Repository: `https://github.com/Big-Tree/HomeAssistant-OPTISPARK`
3. Category: `Integration`

### Download Integration

4. HACS -> 🔍OPTISPARK -> DOWNLOAD
5. If prompted, restart home assistant

### Configure Integration

6. Settings -> Devices & Services -> + ADD INTEGRATION -> 🔍OPTISPARK
7. Read Configuration section of this readme

## Configuration
To optimise your heat pump we need a few details:

- **Electricity tariff:** We use Octopus's API to get prices for the Agile tariff (wider tariff support coming soon!)
- **Postcode:** This is used to get the electricity prices for your area and weather forecasts to calculate the COP of the heat pump
- **Country:** Currently weather forecasts only work in the UK (other countries coming soon!)
- **Heat pump:** The heat pump to be optimised
- **Power usage of heat pump:** To calculate how much money is being saved
- **(Optional) External house temperature:** - Aids our optimisation algorithm

OPTISPARK is now optimising your heat pump!

# Requirements

- Your heat pump needs to be already setup within Home Assistant
- (Optional) Be on the Octopus Agile electricity tariff.  This is not a requirement for testing the integration, you just won't be saving as much money.  Let us know what kind of tariff you're on and we'll look into supporting it!

# Uninstalling

Simply delete the device and your heat pump will go back to normal operation\
Settings -> Devices & Services -> OPTISPARK -> ⚙️Options -> Delete


### Hi, I'm Marcos 👋

I'm a product leader based in Barcelona. I started as a software engineer and researcher, spent years as a CTO and co-founder building products from scratch, and now work in product management, where I combine technical depth with strategy and people leadership.

Most of my work has been in domains where the product is the algorithm: routing optimization, ML-powered prediction, data platforms and connector frameworks. I like problems where the complexity is real and the data is messy.

**Recently**
- **Stuart** (2022–2026): Head of Product Management for network optimization, leading a 32-person cross-functional team. €40M in cost savings from algorithmic improvements, and a 2pp gain in on-time delivery from an ML model that predicts package readiness.
- **Avancargo** (2017–2022): co-founder, first as CTO and then Head of Product, of a B2B logistics SaaS in Buenos Aires. Grew it from idea to 25k users and a $1M seed round.

<!-- GITHUB:START -->
**Open source**
- [midea-lan](https://github.com/wuwentao/midea-lan): a library for controlling Midea appliances over the local network, used by the Midea AC LAN integration for Home Assistant. I added dishwasher support: delayed start, cancel, door auto-open and wash settings.
- [e-data](https://github.com/uvejota/homeassistant-edata): a Home Assistant integration for Spanish electricity consumption data from Datadis. I contributed fixes to its energy statistics, credited in the maintainer's rework.
- [python-holidays](https://github.com/vacanza/holidays): a Python library of public holidays for countries around the world. I added Barcelona's local holidays.
- [date-holidays](https://github.com/commenthol/date-holidays): worldwide holidays. I added Whit Monday as a Barcelona local holiday (moved a week later in 2015 and 2023), moved La Mercè to Monday when it falls on a Sunday, and added replacement days for years when Whit Monday was already a regional holiday.
- [hass-localtuya](https://github.com/xZetsubou/hass-localtuya): a Home Assistant integration to handle Tuya devices locally. I fixed the device registry listener to use `config_entry_id`, resolving a deprecation warning since Home Assistant 2026.10 and preventing breakage in 2027.10.
- [midea_ac_lan](https://github.com/wuwentao/midea_ac_lan): auto-configure and then control your Midea M-Smart devices (air conditioner, fan, water heater, washer, etc.) over the local network. I added full E1 dishwasher controls (program, delayed start, pause, door auto-open), fixed dishwasher energy and water estimates after state values were lowercased, added per-model estimates for model 76000228, and added readable English and Spanish names for E1 mode, status, progress and run-state sensors.
- [QR-Code-Generator](https://github.com/DeerMaximum/QR-Code-Generator): a Home Assistant integration that creates a camera displaying a custom QR code. I excluded the `text` attribute from the recorder so rendered content such as Wi-Fi passwords isn't stored in plain text in the history database and backups.
- [capistrano3-autoscaling-deploy](https://github.com/marcoschicote/capistrano3-autoscaling-deploy) (my project): a Capistrano plugin that deploys to the in-service instances of an AWS Auto Scaling group, published as a Ruby gem. Brought back to life in 2026 as version 2.0, on the current AWS SDK and with a proper test suite and CI.
<!-- GITHUB:END -->

**Background:** MSc in Computer Science (Universidad de Buenos Aires), MBA (Fundação Getulio Vargas) and a postgraduate in Data Science & AI (Universitat de Barcelona). I've also taught entrepreneurship and published research on privacy and software verification.

Happy to connect with people working on platform, developer tooling or AI/ML product problems: [LinkedIn](https://linkedin.com/in/marcoschicote).

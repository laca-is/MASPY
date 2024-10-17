## Executing Negotiation Parking Example

  - Download negotiation_parking.py
  - Install MASPY
    - pip install maspy-ml
  - Run negotiation_parking.py
    - Python .\negotiation_parking.py   
  - Freely modify variables in "main" and re-run negotiation_parking.py
    - Parking("Parking",<NUMS_SPOTS>)
    - for i in range(<NUM_DRIVERS>)
    - drv_settings: dict = {"budget": [(<MIN_PRICE>,<MAX_PRICE>)],
                    "counter": [<COUNTER_OFFER>],
                    "wait": [<WAIT_TIME>]}

## Results

The following table shows the results for multiple numbers of drivers with these settings:
  - <NUMS_SPOTS> = 100
  - "budget": [(10,12),(10,14),(10,20),(12,14),(12,16)]
  - "counter": [0.4, 0.8, 1, 1.2, 1.4]
  - "wait": [0, 0.5, 0.7, 1, 1.5]}

![Results Table](/AAMAS2025/Negotiation_Results.png)

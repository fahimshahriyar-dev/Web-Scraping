import json
import time
import logging
import re

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException,
    StaleElementReferenceException,
)

try:
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service as ChromeService
    USE_WDM = True
except ImportError:
    USE_WDM = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
#  CAR DATA — Add any Porsche model/trim URL here.
#  Category IDs (IRA, IMG, IAS, etc.) are now discovered DYNAMICALLY at runtime.
# ══════════════════════════════════════════════════════════════════════════════
CAR_DATA = {
    "911": {
        "base_image": (
            "https://prs.porsche.com/iod/image/US/9921B2/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQHk0hOMXlKCUMSollT8iAAW+FBIqCBsHAAiAIIAmnIgisqBzCEgCuKsAK5gLnFuIACcFQBMAIwAQtXpmQFBoJCFzvQAngDCEAYcAKoAyulYA7T8KbSaKNUADNUAbH5ZQSQgCwCK6bUA4gAc6QDMIwAs6ecAYstX+wAKV0P16QCshwAa75-fVMsASRO6WWADldlQAOxJAAy6QqD2OVAqAC0AKLpNEAWSaVH2tWu6QBADVcSAAQB1YFUGH7AAqCQASnCqA8ABLpbZvJKcxkVTlDJEgIYPflUYm9Mko2pjMiWKwgQi0XBRBBtEAwCD0HC6EAAKwUtCQVFwjECCk0Nl0MDQ-CVliAA?clientId=icc"
        ),
        "trims": [
            {
                "name": "911 Carrera",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/9921B2"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/9921B2/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQHk0hOMXlKCUMSollT8iAAW+FBIqCBsHAAiAIIAmnIgisqBzCEgCuKsAK5gLnFuIACcFQBMAIwAQtXpmQFBoJCFzvQAngDCEAYcAKoAyulYA7T8KbSaKNUADNUAbH5ZQSQgtQDiABzpAMwjACzpxwBiy2fbAApnQ-XpAKwVj1RPABof6csAkgc-AByAEV0gB2JIAGXSFRu+yoFQAWgBRdJJACySXSyPRTSo21q53SvwAaniQL8AOoAqiQ7YAFQSACVoVRAacqDcABLpYFPLFUYFMiq8obwkBDG4iqgk3rkxG1MZkSxWECEWi4KIINogGAQeg4XQgABWCloSCouEYgQUmhsuhgaH46ssQA?clientId=icc"
                ),
            },
            {
                "name": "911 Carrera T",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/992182"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/992182/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQHk0hOMXlKCUMSollT8iAAW+FBIqCBsHAAiAIIAmnIgisqBzCEgCuKsAK5gLnFuIACcFQBMAIwAHNXpmQFBoJCFzvQAngDCEAYcAKoAyulYA7T8KbSaKNUADNUAbH5ZQSQgtUnptQDi9ekAzABSFccjACzplwBiyzdDAELpAKwAGu-pywCSR98AOQAiukAOxJAAy6QqAAVDlQKgAtACi6V69QAKulkmMqMiALJNKh7BYAdXSPwAakSQD9Sf8qBC9hiEgAlKFUIGXEGc1nnTlDeEgSm9GmknZURG1MZkSxWECEWi4KIINogGAQeg4XQgABWCloSCouEYgQUmhsuhgaH4issQA?clientId=icc"
                ),
            },
            {
                "name": "911 Carrera S",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/9921S2"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/9921S2/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQHk0hOMXlKCUMSollT8iAAW+FBIqCBsHAAiAIIAmnIgisqBzCEgCuKsAK5gLnFuIACcFQBMAIwAytXpmQFBoJCFzvQAngDCEAYcAKr16VgDtPwptJoo1QAM1QBsfllBJCDzAIrptQDiABzpAMz1ACzpZwBiS5d7AAqXQwBC6QCsABof6UsAksc-AByOyoAHYkgAZdIVe5HKgVABaAFF0r0DgAVdJIgCyTSoe1qV3SvwAaniQL8AOoAqgQvbohIAJShVHuAAl0ls3klOYyKpyhnCQEN7vyqCTeuSEQ0QGRLFYQIRaLgogg2iAYBB6DhdCAAFYKWhIKi4RiBBSaGy6GBofhKyxAA?clientId=icc"
                ),
            },
            {
                "name": "911 Carrera 4S",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/9924S2"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/9924S2/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQHk0hOMXlKCUMSollT8iAAW+FBIqCBsHAAiAIIAmnIgisqBzCEgCuKsAK5gLnFuIACcFQBMACwAytXpmQFBoJCFzvQAngDCEAYcAKr16VgDtPwptJoo1QAM1QBsfllBJCDzQwBC6QCMAOIAHOl1FQDMe6e1F3sA+gASAOzp5-W16bUAYkufBwAKnx26QArAANMHpJYASXOUIAcgBFdJPJIAGXSRwq6Qq-xOVAqAC0AKLpXpHAAq6WJAFkmlQDod0tCAGr0kDQgDqcKoaIOFISACUMVR-g90oiQUkJYLsVREUN8SAhv85SAWb12YS9qMyJYrCBCLRcFEEG0QDAIPQcLoQAArBS0JBUXCMQIKTQ2XQwND8I2WIA?clientId=icc"
                ),
            },
            {
                "name": "911 Carrera GTS",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/992142"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/992142/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQHk0hOMXlKCUMSollT8iAAW+FBIqCBsHAAiAIIAmnIgisqBzCEgCuKsAK5gLnFuIACcFQBMAIwALNXpmQFBoJCFzvQAngDCEAYcAKoAyulYA7T8KbSaKNUADNUAbH5ZQSQgtQDiABzptQAS6QDMI-Xp9QBiy5fbAAqXQwBC6QCsu2lUbwAaP+nLK61AEASROAIAckl0gB2JIAGXSFXu+yoFQAWgBRdJJf5UTEAWSaVG2tSu6RBADViSAQQB1cFUeHbAAqCQASoiqABFerc9Lc9kVAVDVEgSm9Gno2pjMiWKwgQi0XBRBBtEAwCD0HC6EAAKwUtCQVFwjECCk0Nl0MDQ-CVliAA?clientId=icc"
                ),
            },
            {
                "name": "911 Carrera 4 GTS",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/992442"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/992442/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQHk0hOMXlKCUMSollT8iAAW+FBIqCBsHAAiAIIAmnIgisqBzCEgCuKsAK5gLnFuIACcFQBMACy11emZAUGgkIXO9ACeAMIQBhwAqgDK6Vj9tPwptJoo1QAM1QBsfllBJCDzADLpAIwA4gAc6QDMw7XptQBiS5f7AAqXgwBC6QCsh2lUbwAaP+lLK67AEASROAIAckl0gB2JI7KgVe7HREALQAoukkv8qOiALKNKj7A7pEEANUJIBBAHVwVQtvsACoJABKCJAAEVahz0hyWRVeYMUSAyT1KajdqMyJYrCBCLRcFEEK0QDAIPQcLoQAArBS0JBUXCMQIKTQ2XQwND8eWWIA?clientId=icc"
                ),
            },
            {
                "name": "911 Carrera Cabriolet",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/9923B2"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/9923B2/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQHk0hOMXlKCUMSollT8iAAW+FBIqCBsHAAiAIIAmnIgisqBzCEgCuKsAK5gLnFuIACcFQBMAMwAQtXpmQFBoJCFzvQAngDCEAYcAKoAyulYA7T8KbSaKNUADNUAbH5ZQSQgAIwA4gAc6VsAaukALABiy2c7AApnQ-XpAKx7ABrPr+9UywCStekAdiSABl0hUbgCwQAtACi6QSFXSMIAsk0qDstud0j8jmiQD8AOr-KjAnYAFQSACVQVQbgAJdIARSeSSZlMRVEZQwOVCGNw5ICOvTxUK2YzIlisIEItFwUQQbRAMAg9BwuhAACsFLQkFRcIxAgpNDZdDA0PwZZYgA?clientId=icc"
                ),
            },
            {
                "name": "911 Carrera T Cabriolet",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/992382"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/992382/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQHk0hOMXlKCUMSollT8iAAW+FBIqCBsHAAiAIIAmnIgisqBzCEgCuKsAK5gLnFuIACcFQBMAMwAHNXpmQFBoJCFzvQAngDCEAYcAKoAyulYA7T8KbSaKNUADNUAbH5ZQSQgAIwA4vXpWwASBwBq6QAsAGLLFzsAChdDAELpAKwAGu-pywCStekAdiSABl0hU7gCwQAtACi6V69QAKulkmMqDCALJNKg7BYAdXSPxO2JAPzx-yowJ2iISACVQVQAIrnRnpRm0ipsob7KgnXokvFJdJQrZjMiWKwgQi0XBRBBtEAwCD0HC6EAAKwUtCQVFwjECCk0Nl0MDQ-GlliAA?clientId=icc"
                ),
            },
            {
                "name": "911 Carrera S Cabriolet",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/9923S2"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/9923S2/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQHk0hOMXlKCUMSollT8iAAW+FBIqCBsHAAiAIIAmnIgisqBzCEgCuKsAK5gLnFuIACcFQBMAMwAytXpmQFBoJCFzvQAngDCEAYcAKr16VgDtPwptJoo1QAM1QBsfllBJCAAjADiABzpmwBq6QAsAGJLp9sACqdDAELpAKwAGi-pSwCStekA7EkAGXSFWuv2BAC0AKLpXq7AAq6UhAFkmlRtpt0uizulPodUSBPgB1H5UAHbOEJABKQKo1wAEukAIpPJJMykVJlDfZUIbXDlUQ69fHgzajMiWKwgQi0XBRBBtEAwCD0HC6EAAKwUtCQVFwjECCk0Nl0MDQ-GlliAA?clientId=icc"
                ),
            },
            {
                "name": "911 Carrera 4S Cabriolet",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/9926S2"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/9926S2/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQHk0hOMXlKCUMSollT8iAAW+FBIqCBsHAAiAIIAmnIgisqBzCEgCuKsAK5gLnFuIACcFQBMAGwAytXpmQFBoJCFzvQAngDCEAYcAKr16VgDtPwptJoo1QAMdX5ZQSQg80MAQukAjADiABy7AGrp1QAsFQDMO2eXNwD6ALJNVOcAYrXp53sACt9bdIAVgAGiD0rUAJJXdIAdiSABl0gcKukKr9YWiAFoAUXSvQOABV0jiXuk9vt0pDjq8QJCAOowqgIvaEhIAJSRVF+AAl0gBFIFJAXs1FUflDI5UIa-MUgY69WlYnajMiWKwgQi0XBRBBtEAwCD0HC6EAAKwUtCQVFwjECCk0Nl0MDQ-C1liAA?clientId=icc"
                ),
            },
            {
                "name": "911 Carrera GTS Cabriolet",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/992342"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/992342/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQHk0hOMXlKCUMSollT8iAAW+FBIqCBsHAAiAIIAmnIgisqBzCEgCuKsAK5gLnFuIACcFQBMAMwALNXpmQFBoJCFzvQAngDCEAYcAKoAyulYA7T8KbSaKNUADNUAbH5ZQSQgAIwA4gAc6VsAaun1AGLLpzsACqdDAELpAKx7aVRPABof6ctnWz8ASVq6QA7EkADLpCrXEFQgBaAFF0kl-lQkt8qAiALJNKg7LZndIAo64kAAgDqwKo4J2ABUEgAlSFUACK9RZ6RZDIqnKGByoR16pLhWzGZEsVhAhFouCiCDaIBgEHoOF0IAAVgpaEgqLhGIEFJobLoYGh+NLLEA?clientId=icc"
                ),
            },
            {
                "name": "911 Carrera 4 GTS Cabriolet",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/992642"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/992642/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQHk0hOMXlKCUMSollT8iAAW+FBIqCBsHAAiAIIAmnIgisqBzCEgCuKsAK5gLnFuIACcFQBMAGwALNXpmQFBoJCFzvQAngDCEAYcAKoAyulYA7T8KbSaKNUADHV+WUEkIACMAOIAHOkbAGrp9QBitcdbAArHQwBC6QCsO2lUDwAab+m1JxtfAJIAZnSAHYkgAZdIVS7AyEALQAoukkp8qPCALJNKhbX5Y7bpP4HTEgP4AdSBVDBWwAKgkAEoQqgARXqjPSjNpFTZQz2VAOvSJsI2YzIlisIEItFwUQQbRAMAg9BwuhAACsFLQkFRcIxAgpNDZdDA0PwJZYgA?clientId=icc"
                ),
            },
            {
                "name": "911 Targa 4S",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/9925S2"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/9925S2/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQHk0hOMXlKCUMSollT8iAAW+FBIqCBsHAAiAIIAmnIgisqBzCEgCuKsAK5gLnFuIACcFQBMAKwAytXpmQFBoJCFzvQAngDCEAYcAKr16VgDtPwptJoo1QAM1QBsfllBJCDzQwBC6QCMAOIAHPsAaunVACwVAMx7F9d3APoAsk1UlwBiS+mXBwAKvx26VqAA1QeklgBJG7pADsSQAMukjhV0hV-nD0QAtACi6V6RwAKulcW90gdDukoad3iAoQB1WFUREHIkJABKyKo-wAEukAIq1JKCjloqgCoYnKhDf7ikCnXp07F7UZkSxWECEWi4KIINogGAQeg4XQgABWCloSCouEYgQUmhsuhgaH42ssQA?clientId=icc"
                ),
            },
            {
                "name": "911 Targa 4 GTS",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/992542"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/992542/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQHk0hOMXlKCUMSollT8iAAW+FBIqCBsHAAiAIIAmnIgisqBzCEgCuKsAK5gLnFuIACcFQBMAKwALNXpmQFBoJCFzvQAngDCEAYcAKoAyulYA7T8KbSaKNUADNUAbH5ZQSQgCwAy6QCMAOIAHPsAaun1AGLLFwcAChdDAELptUdpVLUAGl-py5d7P4ASQAzOkAOxJXZUCp3cHpCoALQAoukkr8qMiALJNKgHQ7pIGnXEgIEAdTBVG2BwAKgkAErQkAARXqzPSzPpFQ5QxOVFOvRJiL2YzIlisIEItFwUQQbRAMAg9BwuhAACsFLQkFRcIxAgpNDZdDA0PwpZYgA?clientId=icc"
                ),
            },
            {
                "name": "911 Turbo 50 Years",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/992470"
                ),
                "price": "null",
                "image": (
                    "https://pictures.porsche.com/rtt/iris?COSY-EU-100-1711coMvsi60AAt5FwcmBEgA4qP8iBUDxPE3Cb9pNXkBuNYdMGF4tl3U0%25z8rMHIspbWvanYb%255y%25oq%25vSTmjMXD4qAZeoNBPUSfUx4RmHlCgI7Zl2dioCLNeQDcFG8oXYnfurn205yPewDa2CvNzxKEYGXoq1SoUr6FObKHTBsN5n3g2dEhev5HFhLHnd7pQpqZYoOaD8JiXvBCY"
                ),
            },
            {
                "name": "911 Turbo S",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/992452"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/992452/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQHk0hOMXlKCUMSollT8iAAW+FBIqCBsHAAiAIIAmnIgisqBzCEgCuKsAK5gLnFuIACcFQBMACwArNXpmQFBoJCFzvQAngDCEAYcAKoAyulYA7T8KbSaKNUADNUAbH5ZQSQgAIwA4gAc6VsAEukAzAAytWcjV1S1AGLL6bU7AArPQwBC6fV7AFo-AAagPSy3uW1BAElTqCAHLfKgAdiS53SFVeByoFT+AFF0jiALJNKg7XbpSEANWJIEhAHUYVRzjsACoJABKqKoAEUtgApdJctkVAVDTEgCm9akUgFUP5bMZkSxWECEWi4KIINogGAQeg4XQgABWCloSCouEYgQUmhsuhgaH4qssQA?clientId=icc"
                ),
            },
            {
                "name": "911 Turbo S Cabriolet",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/992652"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/992652/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQHk0hOMXlKCUMSollT8iAAW+FBIqCBsHAAiAIIAmnIgisqBzCEgCuKsAK5gLnFuIACcFQBMAGwArNXpmQFBoJCFzvQAngDCEAYcAKoAyulYA7T8KbSaKNUADHV+WUEkIACMAOIAHOkbAGrp1QCy6QDMADIALOnXAGK1d1sACndDAELp9TsAWt8ADQB6Vq9w2IIAkud0gB2JKXdIVF4wxG-ACi6TRJyaVC223SEIOOJAEIA6tCqJctgAVBIAJQRVAAihsAFLpJl0iocoZ7KgHXrEg7-Ki-DZjMiWKwgQi0XBRBBtEAwCD0HC6EAAKwUtCQVFwjECCk0Nl0MDQ-FlliAA?clientId=icc"
                ),
            },
            {
                "name": "911 GT3",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/992812"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/992812/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQHU4UVgBUArlBQtPxyIIrKUMSollT8iAAW+FBIqCBsHAAiAIIAmqHhBJHMMSAK4qx+YC5pbiAAnHUATAAcAIyN+UqFUaCQAbj0AJ4AwhAGHACqAMqhWGPBObSaKI0ADI0AbPJdKsgkIKsAiqGtAMwnAOLNoQAsWedUNwCS148TAEKhAKwAGj+hGwAcllQgB2LIAGVCdQACq8QMNGscqBdWsNQk8AGodKhPdwPEAQi4+DIAJShVEON2RIEOpLqoUOE3hmMRoQAWq0ZmRLFYQIRaLgkggeiAYBB6DhdCAAFYKWhIKgDDCEBSaGy6GBofgCyxAA?clientId=icc"
                ),
            },
            {
                "name": "911 GT3 with Touring Package",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/992822"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/992822/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQHU4UVgBUArlBQtPxyIIrKUMSollT8iAAW+FBIqCBsHAAiAIIAmqHhBJHMMSAK4qx+YC5pbiAAnHUATAAcjY35SoVRoJABuPQAngDCEAYcAKoAyqFYo8E5tJoojQAMjQBs8p0qyCQgAIwA4s2hAMz7oQAsWadXAJInVJfjAEKhAKwAGp+h6wByAEVQgB2LIAGVCdQACo8QENGkCqIcVu5QncAGrtKh3dy3Khgw4+DIAJQhVD+l1CAMuiJAAOJdSp41h6PhoQAWvtpmRLFYQIRaLgkghuiAYBB6DhdCAAFYKWhIKj9DCEBSaGy6GBofgCyxAA?clientId=icc"
                ),
            },
            {
                "name": "911 GT3 RS",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/992850"
                ),
                "price": "null",
                "image": (
                    "https://pictures.porsche.com/rtt/iris?COSY-EU-100-1711coMvsi60AAt5FwcmBEgA4qP8iBUDxPE3Cb9pNXkBuNYdMGF4tl3U0%25z8rMHIspbWvanYb%255y%25oq%25vSTmjMXD4qAZeoNBPUSfUx4RmHlCgI7Zl2dioCxkF%25vUqCNwuWXsOw3meV6iTCj%25zhRc2GRdqAZ%25oD21P%25S1BAXmenugTfeIJpV7nDhQT"
                ),
            },
            {
                "name": "911 Spirit 70",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/992352"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/992352/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQHk0hOMXlKCUMSollT8iAAW+FBIqCBsHAAiAIIAmnIgisqBzCEgCuKsAK5gLnFuIACcFQBMAMwArNXpmQFBoJCFzvQAngDCEAYcAKoAyulYA7T8KbSaKNUADNUAbH5ZQSQgCwBq6QCMAOIAHOm1ADIALOkXAGLL1wcACtdDAELp9RUAounLCQDSvxuFV+AElaukAOxJM7pCqPSFwgBaPyoSUezzRQwO6VeIwS6S+AFkmlQvu50gc9jd0qDtqSQKCAOoQqhnA4AFQSACVYVQAIp7ABS6X53JBAqGJyoHIW6SGRLlVG2vQZSL2YzIlisIEItFwUQQbRAMAg9BwuhAACsFLQkFRcIxAgpNDZdDA0Pw9ZYgA?clientId=icc"
                ),
            }
        ],
    },
    "Taycan": {
        "base_image": (
            "https://prs.porsche.com/iod/image/US/Y1AAI1/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQHk0hOMXlKCUMSollT8iAAW+FBIqCBsHAAiAIIAmnIgisqBzCEgCuKsAK5gLnFuICkAjElJAJKV6ZkBQaCQhc70AJ4AwhAGHACqAMrpWH20-Cm0migATAAMswBsfllBJCDzAIrp2wDi6ZV7ABzpAMwAQgAs5wAyN1RXAOwHjwBiS+lXe29fAxdfAAaDxAAFZAYD0ktamcoQBpACcUIAcjsqE95pD0WcAKLpJ5JW74lKnKgIgAKT3SCIAWniqDV0nUkVQ9pUsSBas90rUAGqzHkAdVhVFuewAKgkAEpEqjIgBSArlgpBWyO6S2UpZIC2A1JOsFoPSvO6ArIlisIEItFwUQQLRAMAg9BwuhAACsFLQkFRcIxAgpNDZdDA0PxrZYgA?clientId=icc"
        ),
        "trims": [
            {
                "name": "Taycan",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/Y1AAI1"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/Y1AAI1/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQHk0hOMXlKCUMSollT8iAAW+FBIqCBsHAAiAIIAmnIgisqBzCEgCuKsAK5gLnFuICkAjElJAJKV6ZkBQaCQhc70AJ4AwhAGHACqAMrpWH20-Cm0migATAAMswBsfllBJCDzAIrp2wDi6ZV7ABzpAMwAQgAs5wAyN1RXAOwHjwBiS+lXe29fAxdfAAaDxAAFZAYD0ktamcoQBpACcUIAcjsqE95pD0WcAKLpJ5JW74lKnKgIgAKT3SCIAWniqDV0nUkVQ9pUsSBas90rUAGqzHkAdVhVFuewAKgkAEpEqjIgBSArlgpBWyO6S2UpZIC2A1JOsFoPSvO6ArIlisIEItFwUQQLRAMAg9BwuhAACsFLQkFRcIxAgpNDZdDA0PxrZYgA?clientId=icc"
                ),
            },
            {
                "name": "Taycan Black Edition",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/Y1AGI1"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/Y1AGI1/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQHk0hOMXlKCUMSollT8iAAW+FBIqCBsHAAiAIIAmnIgisqBzCEgCuKsAK5gLnFuICkAjEkA4gCSlemZAUGgkIXO9ACeAMIQBhwAqgDK6Vj9tPwptJooAEwADHMAbH5ZQSQgCwCKPemVNQAc6XMAKukAzABCACzpNwBiy-eDV-cAGndUAKzv7+nLb4AaQBdQuAKBAE4AQA5bbpADsC3+VARFwAooikgAZREpY5USEABQR6UhAC1MVQknVodSAErpGqVFEgAASN0G6TqADU5tyAOrgqhApL8qjYmqnBL03FUGEAKXFIBhAq+IG2cwV6W29LpGsGBI1Au+6R5PX5ZEsVhAhFouCiCFaIBgEHoOF0IAAVgpaEgqLhGIEFJobLoYGh+HbLEA?clientId=icc"
                ),
            },
            {
                "name": "Taycan 4",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/Y1ABN1"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/Y1ABN1/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQHk0hOMXlKCUMSollT8iAAW+FBIqCBsHAAiAIIAmnIgisqBzCEgCuKsAK5gLnFuICkAjEkAQgBylemZAUGgkIXO9ACeAMIQBhwAqgDK6Vj9tPwptJooAEwADHMAbH5ZQSQgCwCKAOLpC4M16ZW7ABzpAMw1ACxXADJ3VDcA7PvPAGLL6Te7Hz9HH4ADSeIAArJVLgsFukIVCFgB9ACyc1hQKB6WWAElLpiANIATkxdW26ReCwxVBelwAomSkvcySkLlQzkSqASAAovdIEgBadKoSSS6SSWPZIF2lUpICxr3SWIAaqiqFiAOq4qj3XYAFQSACVGVQ6gApFUgOpq0HbU7pbb6iXbQYskDbNVg9KKnqosiWKwgQi0XBRBCtEAwCD0HC6EAAKwUtCQVFwjECCk0Nl0MDQ-EDliAA?clientId=icc"
                ),
            },
            {
                "name": "Taycan 4 Black Edition",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/Y1AHN1"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/Y1AHN1/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQHk0hOMXlKCUMSollT8iAAW+FBIqCBsHAAiAIIAmnIgisqBzCEgCuKsAK5gLnFuICkAjEkAEgBylemZAUGgkIXO9ACeAMIQBhwAqgDK6Vj9tPwptJooAEwADHMAbH5ZQSQgCwCKPemVAOIAHOlzACrpAMwAQgAs6bcAYssPg9cPABr3VACsHx-pZY-ADSgIAkpdAcCAJyAurbdIAdgWAKoiMuAFEkUkADJIlInKjQgAKiPS0IAWliqEkwbCaQAldIHSqokA1W6DdJggBqc25AHVIVRgUl+VQcQczgkGXiqHUAFLikB1AXfEDbOYK9LbBn0jWDQkagU-dI8nr8siWKwgQi0XBRBCtEAwCD0HC6EAAKwUtCQVFwjECCk0Nl0MDQ-DtliAA?clientId=icc"
                ),
            },
            {
                "name": "Taycan 4S",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/Y1ADJ1"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/Y1ADJ1/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQHk0hOMXlKCUMSollT8iAAW+FBIqCBsHAAiAIIAmnIgisqBzCEgCuKsAK5gLnFuICkAjEkJAFKV6ZkBQaCQhc70AJ4AwhAGHACqAMrpWH20-Cm0migATAAMswBsfllBJCDzAIoA4umVOwAc+wCS6QDMAEIALBcAMrdU1wDse08AYkvp1zvv3wOXb4ADUeIAArECgeklidztCANIATmhADktulnvMoVRnucAKIYpJ3DEpY5UREABWe6URAC0CVQkkl0kkTsiqDtKtiQCcXukTgA1Wb8gDqcKodx2ABUEgAlYlUFG1YWKkWgrYHdJbWXskBbAZkvUisHpAXdYVkSxWECEWi4KIIFogGAQeg4XQgABWCloSCouEYgQUmhsuhgaH4tssQA?clientId=icc"
                ),
            },
            {
                "name": "Taycan 4S Black Edition",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/Y1AJJ1"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/Y1AJJ1/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQHk0hOMXlKCUMSollT8iAAW+FBIqCBsHAAiAIIAmnIgisqBzCEgCuKsAK5gLnFuICkAjEkAUjWV6ZkBQaCQhc70AJ4AwhAGHACqAMrpWH20-Cm0migATAAMswBsfllBJCDzAIrd6ZUA4gAc6bMAKukAzABCACzpNwBiS-cDV-cAGndUAKzv7+lLb4AaQBAEkLgCgQBOAEAOS26QA7PN-lRERcAKJIpIAGSRKWOVChAAVEekoQAtLFUJKgmE0gBK6X2lVRIAAEjcBulQQA1WY8gDqEKoQKSAqoOP2pwSDLxVFhNQlIFhgq+IC2sxq6S2DPpGoGhI1gu+6V53QFZEsVhAhFouCiCBaIBgEHoOF0IAAVgpaEgqLhGIEFJobLoYGh+HbLEA?clientId=icc"
                ),
            },
            {
                "name": "Taycan GTS",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/Y1ADK1"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/Y1ADK1/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQHk0hOMXlKCUMSollT8iAAW+FBIqCBsHAAiAIIAmnIgisqBzCEgCuKsAK5gLnFuICkAjEkJANKV6ZkBQaCQhc70AJ4AwhAGHACqAMrpWH20-Cm0migATAAMswBsfllBJCDzADLp8wCKAHLplQDiABzHABoAYukAzABCACzpT9dLrye3VE8DD6+XF5UACsdwAWulgZdLuklgBJO6w2oATlhBwAKukAOzzGFULF3ACi2KSO3xKQuVGRAAUselkWDiVQTpU8SA4QA1WbpOEAdURVC2J3RCQASmSQAcAFLcqgHXlAkB7SpS9J7O4fKh7UWorUDSlK3nA9JDAAS6Q53W5ZEsVhAhFouCiCBaIBgEHoOF0IAAVgpaEgqLhGIEFJobLoYGh+A7LEA?clientId=icc"
                ),
            },
            {
                "name": "Taycan Turbo",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/Y1AFL1"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/Y1AFL1/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQHk0hOMXlKCUMSollT8iAAW+FBIqCBsHAAiAIIAmnIgisqBzCEgCuKsAK5gLnFuICkAjEkAYgAylemZAUGgkIXO9ACeAMIQBhwAqgDK6Vj9tPwptJooAEwADHMAbH5ZQSQgCwCK6TsA4umV+wAc6QDMAEIALBcA0odU1zXL6df7NW+Dl28AGrdUACsv1+6WW1wAWmCAJLnMF3ACcYIAcgAVdIAdgWoKoGPOAFFMUk6piUmcqAiAAoY9IIiGEqj7So4kDQgBqc3S0IA6nCqHV9qiEgAlElUZEAKU54u5AJA2zmEvS23Oryo22FSPVg3J8u5gPSbJ60pAbKVZEsVhAhFouCiCFaIBgEHoOF0IAAVgpaEgqLhGIEFJobLoYGh+DbLEA?clientId=icc"
                ),
            },
            {
                "name": "Taycan Turbo S",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/Y1AFM1"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/Y1AFM1/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQHk0hOMXlKCUMSollT8iAAW+FBIqCBsHAAiAIIAmnIgisqBzCEgCuKsAK5gLnFuICkAjEkAYgCylemZAUGgkIXO9ACeAMIQBhwAqgDK6Vj9tPwptJooAEwADHMAbH5ZQSQgCwCKAOLplbsAHOkAzABCACzplzXLN7s1N4PnNwAa11QArG9v6ctfADS-wAkqd-oCAJz-AByABV0gB2BZ-KiI04AUSRSQAMkiUicqJCAAqI9KQgBaWKoSUaVF2lVRIBBADU5ukQQB1cFUHG7OEJABKeKoMIAUuzRZzPiBtpUxeltoLoVRtoNCbLOV90iyepKQCyFWRLFYQIRaLgoghWiAYBB6DhdCAAFYKWhIKi4RiBBSaGy6GBofjmyxAA?clientId=icc"
                ),
            },
            {
                "name": "Taycan Turbo GT",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/Y1AFT1"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/Y1AFT1/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQHU4UVgBUArlBQtPxyIIrKUMSollT8iAAW+FBIqCBsHAAiAIIAmqHhBJHMMSAK4qx+YC5pbiA5AIxZAGI+9flKhVGgkAG49ACeAMIQBhwAqgDKoVgjwTm0migATAAMSwBs8h0qyCQgK+uhKwCKAHJHPqH1AOIAHKFLgwDsoQDMAEIALG8ACudUnyyr1Cn2uABkQQBJe4AsbvEEADW+VAArAiEaF1iiAFKYyHAqjrADSAE5MadLlQnlkIVScjCQCSfi8qCSAFoAUVC13qGKokIAaktQpD3ASQGDrj4MgAlWkgU7uZEgY71XFUY4yskasYM47uFGhAWDYVkSxWECEWi4JIILogGAQeg4XQgABWCloSCofQwhAUmhsuhgaH4VssQA?clientId=icc"
                ),
            },
            {
                "name": "Taycan Turbo GT with Weissach Package",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/Y1AFP1"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/Y1AFP1/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQHU4UVgBUArlBQtPxyIIrKUMSollT8iAAW+FBIqCBsHAAiAIIAmqHhBJHMMSAK4qx+YC5pbiA5AIxZAGIACvX5SoVRoJABuPQAngDCEAYcAKoAyqFYo8E5tJooAEwADMsAbPKdKsgkIKsArKGrAIoAcqH1AOIAHKEAzC2XVAAsWQ+hr9cAMl8Akvc3uMAEKhQ4ADQhoQ2hwAUjD-p8qBsANIAThh5x8oQA7Fk-lRbgiqOiWrjQllJoSQNd6tCqP8AGrLUL-dzIkCogASxyoP2uPgyACUaed3K9Qqd6iSQKdhZiqKdxkC5e4+SAmUNWWRLFYQIRaLgkghuiAYBB6DhdCAAFYKWhIKj9DCEBSaGy6GBofiGyxAA?clientId=icc"
                ),
            },
            {
                "name": "Taycan Sport Turismo",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/Y1CAI1"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/WW/Y1CAI1/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQHk0hOMXlKCUMSollT8iAAW+FBIqCBsHAAiAIIAmnIgisqBzCEgCuKsAK5gLnFuICkAjADCSQCSlemZAUGgkIXO9ACe1RAGHADqA+lYfbT8KbSaKABMAAwzAGx+WUEkIJUAKgDM6dtJjVQALADsAGLpRwDiF1QArAAa1emLdbtUiwDSAJzpJ4vPKgnJKfdLfABaAFF0kkkukEnN0ldKg90nUjjM0QN3iAAFKQnEAGSumwSACVCekAIqVK7Usm-KhUgBqOKpAzu6WZhMxZEsVhAhFouCiCFaIBgEHoOF0IAAVgpaEgqLhGIEFJobLoYGh+ELLEA?clientId=icc"
                ),
            },
            {
                "name": "Taycan Sport Turismo Black Edition",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/Y1CGI1"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/WW/Y1CGI1/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQHk0hOMXlKCUMSollT8iAAW+FBIqCBsHAAiAIIAmnIgisqBzCEgCuKsAK5gLnFuICkAjADCAOIAkpXpmQFBoJCFzvQAntUQBhwA6oPpWP20-Cm0migATAAMswBsfllBJCDzAHLV6ZUAKgDM6bP76YdJTVQArAAau1RL1wDS6Uv1x4-PAJzpAOxLB4gP5JV5UP63a7-FIADnS3wAWgBRdJJABK6QAYkd0rVKrd0gAJAAsAFV0vVBp8QAApJHU55JJbpAAytX2CTRLPSAEVZjTeWjflQeQA1ak8wZQqiilmzEBkSxWECEWi4KIINogGAQeg4XQgABWCloSCouEYgQUmhsuhgaH4qssQA?clientId=icc"
                ),
            },
            {
                "name": "Taycan 4S Sport Turismo",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/Y1CDJ1"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/WW/Y1CDJ1/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQHk0hOMXlKCUMSollT8iAAW+FBIqCBsHAAiAIIAmnIgisqBzCEgCuKsAK5gLnFuICkAjADCCQBSlemZAUGgkIXO9ACe1RAGHADqA+lYfbT8KbSaKABMAAwzAGx+WUEkIJUAKgDM6dtJjVQALADsAOLpR2cAYukArAAa1emLAJK7VIsA0gCc6SeLZ5UE5JL7pAAcdXSPwAWgBRdJJJLpM6VB7pV5HGYYgYfEB1OF4gAyZ02CQASkT0gBFSoXKjU8l-BkANTx1IGd3SLKJ2LIlisIEItFwUQQrRAMAg9BwuhAACsFLQkFRcIxAgpNDZdDA0PxhZYgA?clientId=icc"
                ),
            },
            {
                "name": "Taycan 4S Sport Turismo Black Edition",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/Y1CJJ1"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/WW/Y1CJJ1/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQHk0hOMXlKCUMSollT8iAAW+FBIqCBsHAAiAIIAmnIgisqBzCEgCuKsAK5gLnFuICkAjADCAFK1lemZAUGgkIXO9ACe1RAGHADqA+lYfbT8KbSaKABMAAwzAGx+WUEkIHMActXplQAqAMzpM3vpB0mNVACsABo7VItXANLpiwCSRw9PAJzpAOyLe4gP5JF5UP43K7-FIADnS3wAWgBRdJJABK6QAYod0gBxSo3dIACQALABVdJvAafEC1JE0p5JRbpAAyuL2CTRLPSAEUZrVeWjflQeQA1Gk8gZQqiilkzEBkSxWECEWi4KIIVogGAQeg4XQgABWCloSCouEYgQUmhsuhgaH4qssQA?clientId=icc"
                ),
            },
            {
                "name": "Taycan GTS Sport Turismo",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/Y1CDK1"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/Y1CDK1/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQHk0hOMXlKCUMSollT8iAAW+FBIqCBsHAAiAIIAmnIgisqBzCEgCuKsAK5gLnFuICkAjADCCQDSlemZAUGgkIXO9ACe1RAGHACqAMrpWH20-Cm0migATAAMswBsfllBJCDzAIoAcumVAOIAHPsAGgBi6QDMAEIALNfnB+l350svB5dUdwM3L6cPKgAViuAC10kDTqd0ksAJJXGF1ACcMJ2ABV0gB2ebQqiYq4AUSxSQAMliUicqEiAAqY9JI0FEqjnebpA6VXEgWEANVm6VhAHUEVQSQc0QkAEpkqg7ABSfJlAsBIC2lVl6S2V3eVC2EpROoGlJVAqB6SGAAl0tzqnyyJYrCBCLRcFEEK0QDAIPQcLoQAArBS0JBUXCMQIKTQ2XQwND8J2WIA?clientId=icc"
                ),
            },
            {
                "name": "Taycan Turbo Sport Turismo",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/Y1CFL1"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/WW/Y1CFL1/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQHk0hOMXlKCUMSollT8iAAW+FBIqCBsHAAiAIIAmnIgisqBzCEgCuKsAK5gLnFuICkAjADCAGIAMpXpmQFBoJCFzvQAntUQBhwA6oPpWP20-Cm0migATAAMswBsfllBJCCVACoAzOmzW+k7SU1UOwDSAOLpACyXtekArAAa1elLNwBa7wCSe1RLc4ATnSAHYlm8qKCkud0kDPgBRdKXSrPdI-G7-EA-QZYgBSCKx9UuWwSACV6ukAIqzPHUskgqhUgBqWKpg0e6WZdKozPqsxAZEsVhAhFouCiCDaIBgEHoOF0IAAVgpaEgqLhGIEFJobLoYGh+GLLEA?clientId=icc"
                ),
            },
            {
                "name": "Taycan Turbo S Sport Turismo",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/Y1CFM1"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/WW/Y1CFM1/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQHk0hOMXlKCUMSollT8iAAW+FBIqCBsHAAiAIIAmnIgisqBzCEgCuKsAK5gLnFuICkAjADCAGIAspXpmQFBoJCFzvQAntUQBhwA6oPpWP20-Cm0migATAAMswBsfllBJCCVACoAzOk7SU1UACwA4rXpAKwAGtXpS5cA0vcAkntUS48AnOkA7Et3Ki-JLPKhfABaAFF0qdKtcYb90i9Bu8QAApSGogAypy2CQASlj0gBFSpokn4n5UYkANVRxMGl3SNPJVBpWNmIDIlisIEItFwUQQbRAMAg9BwuhAACsFLQkFRcIxAgpNDZdDA0Px+ZYgA?clientId=icc"
                ),
            },
            {
                "name": "Taycan 4 Cross Turismo",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/Y1BBN1"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/Y1BBN1/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQGU0-XAAIACvx4tGgArnIgispQxKiWVPyIABb4UEioIGwcACIAggCa4ZEE0cxxIArirCFgLhluIHkAjABCzQByjYVKxTGgkCHO9ACeAMIQBhwAqu7hWOO0-HnB9CgATAAMqwBs8t0qyCQg6wCK4ScA4uGN5wAc4QDMzQAsDwBil1T3ADIvVE8A7B8QE9Xltwk9zq9wZNmuCABq-EAAVjhcPCWwAkvd0QBpACc6Lapyo-3WaJJ9wAouF-jkvjS8ncqHi-P9wniAFrUqg5HLhHIYglUc6NckgDEA8IYgBqqylAHVsVQvucACpZABK9KobRF4TaACk5Tr5YjjtdwscNUKQMdJkzbfKkeFJnC2VRpSM5WRLFYQIRaLgUgheiAYBB6DhdCAAFYKWhIKi4RjRBSaGy6GBeAOWIA?clientId=icc"
                ),
            },
            {
                "name": "Taycan 4S Cross Turismo",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/Y1BDJ1"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/Y1BDJ1/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQGU0-XAAIACvx4tGgArnIgispQxKiWVPyIABb4UEioIGwcACIAggCa4ZEE0cxxIArirCFgLhluIHkAjABCWQBSjYVKxTGgkCHO9ACeAMIQBhwAqu7hWOO0-HnB9CgATAAMqwBs8t0qyCQg6wCKAOLhjTkXpwAc4QDMzQAsDwBi51T3ADIvVE8A7B8QE9Xltwk9Tq9wZNmuCABq-EAAVjhcPCWwAkvd0QBpACc6IAcsdwv91miqP97gBRUk5L6kvJ3Kh4vz-cJ4gBatKoOSuvIxBKop0aFJAGIB4QxADVVlKAOrYqhfU4AFSyACUGVRCSLwoS2nKdfLEcdGkDjhqhSBjpNmTb5UjwtKRnKyJYrCBCLRcCkEL0QDAIPQcLoQAArBS0JBUXCMaIKTQ2XQwLzeyxAA?clientId=icc"
                ),
            },
            {
                "name": "Taycan Turbo Cross Turismo",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/Y1BFL1"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/Y1BFL1/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQGU0-XAAIACvx4tGgArnIgispQxKiWVPyIABb4UEioIGwcACIAggCa4ZEE0cxxIArirCFgLhluIHkAjABCAGIAMo2FSsUxoJAhzvQAngDCEAYcAKru4VgTtPx5wfQoAEwADGsAbPI9KsgkIBsAigDi4Y1nABzhAMzNACz3rRdUdwDSbyCPrdvhjzOrQBU2aAIAGs8qABWcHg8LbR4ALQRAEk7giPgBOBEAOQAKuEAOwbeFUIl3ACixJy7WJeVuVGu7Sy4SxfiJbKR1KoZ0aZJAqIAamtwqiAOoYqjtM74rIAJTpVFxUJAuL54VxAClRcrxaqTmsteETnd-lQTvKcRapoyQCdxdDwkLRrqQELjWRLFYQIRaLgUgg+iAYBB6DhdCAAFYKWhIKi4RjRBSaGy6GBeP2WIA?clientId=icc"
                ),
            },
            {
                "name": "Taycan Turbo S Cross Turismo",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/Y1BFM1"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/Y1BFM1/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQGU0-XAAIACvx4tGgArnIgispQxKiWVPyIABb4UEioIGwcACIAggCa4ZEE0cxxIArirCFgLhluIHkAjABCAGIAso2FSsUxoJAhzvQAngDCEAYcAKru4VgTtPx5wfQoAEwADGsAbPI9KsgkIBsAiuGnAOLhjRcAHOEAzM0ALI+tV1TPrdvhzxetvymzV+AA1XlQAKwgkHhbYQgDSsIAkg9YfCAJywgByABVwgB2DYwqj4h4AUQJOQAMgS8vcqLcqVlwui-PiWQAtClUC6NYkgJEANTW4SRAHVUVQqRccVkAEo0qhY3nhLEAKRFSrF4JAJ0aavCJzlmKoJym9N1Yoh4UFo01IEFBrIlisIEItFwKQQfRAMAg9BwuhAACsFLQkFRcIxogpNDZdDAvO7LEA?clientId=icc"
                ),
            }
        ],
    },
    "Cayenne": {
        "base_image": (
            "https://prs.porsche.com/iod/image/US/X1AAA1/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PWDT84MCPUxN5JQIoYlRLKi8EAAt8KCRUEDYOABEAQQBNORBFZRDmcJAFcVYAVzAXRLcQAA0ARlSG2qyc4NDQSBLnegBPAGEIAw4AVQBlLKwB2n502k0UACYABnmANkDc0JIQRYBFLN2AcSza5IAOY4PzqnmAMSaqABYAaQB2LIedvcehgCEslZWAAl-gBJACs-wAsn8qCsAHJfEAvFapLIvVIAGSyAE4wTCQNiAApvKjYgBa8yyNwAKvcQAdamSsgdIQBmLKAxbsqgggBqlJ5AHVuSAMQdqckAEpYqgY6kCkCQgCiWR2tSOVB2kuxqqGVxAvN6Ct5gqaZEsVhAhFouFiCDaIB89BwuhAACsFLQkFRcIwQgpNDZdDBPNbLEA?clientId=icc"
        ),
        "trims": [
            {
                "name": "Cayenne Electric",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/X1AAA1"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/X1AAA1/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PWDT84MCPUxN5JQIoYlRLKi8EAAt8KCRUEDYOABEAQQBNORBFZRDmcJAFcVYAVzAXRLcQAA0ARlSG2qyc4NDQSBLnegBPAGEIAw4AVQBlLKwB2n502k0UACYABnmANkDc0JIQRYBFAHEs2uSADkO906pagAks+YAxJqoAFgBpAHYsp52dz6GAISyKxWNyoKwAkgBWQEAWQBoIAcj8qG8Vqksm9UgAZLIATghcJAOIACh8qDiAFrzLJ3AAqjxAe1q5Kye2hAGYsldFhyqGCAGpU3kAdR5IExexpyQAStiqJiaYKQNCAKJZHa1A5UHZSnFqoYXEB83qKvlCppkSxWECEWi4WIINogHz0HC6EAAKwUtCQVFwjBCCk0Nl0ME8NssQA?clientId=icc"
                ),
            },
            {
                "name": "Cayenne Turbo Electric",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/X1ACD1"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/X1ACD1/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PWDT84MCPUxN5JQIoYlRLKi8EAAt8KCRUEDYOABEAQQBNORBFZRDmcJAFcVYAVzAXRLcQAA0ARlSAYWTarJzg0NBIEud6AE8GiAMOAFUAZSysQdp+dNpNFAAmAAYFgDZA3NCSECWARQBxLKWAFSza5IAOM-2rqgWAMRaqABYAaQB2LOfd3a-hgCEsqtVvcgQBJACsQIAsoCqKsAHKpLLvVbIqjvVIAGSyAE4AAqfKi4gBaCyy92OTxA+1qJKyAAklgBmLJggBq5KoYIA6qyqFj9sdkgAlHEC45ckC7WoAKSyuxFuIVw1uIHZDSyGql7J5LTIlisIEItFwsQQHRAPnoOF0IAAVgpaEgqLhGCEFJobLoYJ4TZYgA?clientId=icc"
                ),
            },
            {
                "name": "Cayenne",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/9YAAI1"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/9YAAI1/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQFV6AIwwBZNGAYciCKylDEqJZU-IgAFvhQSKggbBwAIgCCAJrBoQThzFEgCuKsAK5gLiluIACcWRkZAJIAjLlK+RGgkGXO9ACeAMIQBhzuAMrBWCO0-Fm0migATAAMSwBs8h0qyCQgK74ArMEtaQAcJwDi6ycAWr7BS4MA7I+3ABLBACwAzACi3wAYjcqF8AIpg77uABCwUOAA14cF1k0fsiANK1ZEAOUhVGe8OO+KybSoZx+aWCZ3GABlgrUAAqvKgZbHBQEAFTRVEuLUuwSaRJATQAaksBQB1bkgGmXDlpABKdKoYJaGWCYIVWKoIsG4p1EtJIFuLUmZEsVhAhFouASCC6IBgEHoOF0IAAVgpaEgqLhGOEFJobLoYGh+NbLEA?clientId=icc"
                ),
            },
            {
                "name": "Cayenne Black Edition",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/9YADI1"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/WW/9YADI1/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQFV6AIwwBZNGAYciCKylDEqJZU-IgAFvhQSKggbBwAIgCCAJrBoQThzFEgCuKsAK5gLiluIACcWRlpAJIAjLlK+RGgkGXO9ACeAMIQBhwA6mPBWCO0-Fm0migATAAMSwBs8h0qyCQgKwCiwS1pAOzHACoAzMFXGW1UACwAYkvBAKynAIofABqDwXWTRuVHWAGlaoCAHIAKWCpwyYPhv3ewQAHFcAELBDIANWCB18IJAz2uwQA4i1ycEmmNiTCDsSADLki5pABKTOCXyWcKoX3ZkP5uJuZEsVhAhFouASCC6IBgEHoOF0IAAVgpaEgqLhGOEFJobLoYGh+FLLEA?clientId=icc"
                ),
            },
            {
                "name": "Cayenne E-Hybrid",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/9YAAV1"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/9YAAV1/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQFV6AIwwBZNGAYciCKylDEqJZU-IgAFvhQSKggbBwAIgCCAJrBoQThzFEgCuKsAK5gLiluIACcWRkZAGoAjLlK+RGgkGXO9ACeAMIQBhzuAMrBWCO0-Fm0migATAAMSwBs8h0qyCQgKwCKwS1pABzHAOLnVC0AWkdUS4MA7MFLtwASwQAsAGLrPwODxA33cACFggBWZ4AOShAA14cF1gBJADMyIA0rVkTDgc8VkiqM80QBRYLPeGQilZNpUU5otLBU7jAAywVqAAVXlQMnCqL8ACoYqgXFoXYIoppLSUAdRFIExYIBVFZF0FaQASuyqDCAFIyqgHFoZYIHTU4qhNQaGkBNWV0kC3FqTMiWKwgQi0XAJBBdEAwCD0HC6EAAKwUtCQVFwjHCCk0Nl0MDQ-C9liAA?clientId=icc"
                ),
            },
            {
                "name": "Cayenne E-Hybrid Black Edition",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/9YADV1"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/WW/9YADV1/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQFV6AIwwBZNGAYciCKylDEqJZU-IgAFvhQSKggbBwAIgCCAJrBoQThzFEgCuKsAK5gLiluIACcWRlpAGoAjLlK+RGgkGXO9ACeAMIQBhwA6mPBWCO0-Fm0migATAAMSwBs8h0qyCQgKwCiwS1pAOzHACoAzMFXGW1UACwAYkvBAKynAIofABqDwXWAEkblR1gBpWqAgByAClgqd1gCqKcMuCEb93sEABxXABCwQyTWCB18oJAz2uwQA4i1qcEgWNybCDuSADLUi5pABKbOCXyW8KoX25UOFTRuZEsVhAhFouASCC6IBgEHoOF0IAAVgpaEgqLhGOEFJobLoYGh+HLLEA?clientId=icc"
                ),
            },
            {
                "name": "Cayenne S",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/9YABJ1"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/9YABJ1/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQFV6AIwwBZNGAYciCKylDEqJZU-IgAFvhQSKggbBwAIgCCAJrBoQThzFEgCuKsAK5gLiluIACcWRkAQgBSAIy5SvkRoJBlzvQAngDCEAYc7gDKwVijtPxZtJooAEwADMsAbPKdKsgkIK1pABzBrQDiG6cAWkPBy0MA7Hc5VMtXABLBAMwAYhnBABYfpcqACAIpgwHuRrBACsDwACnDfP8qLCABro4IbACSX2xAGlatiAHKQqgPdGw4IPLLtKhHL5pYJHCYAGWCtQRTyoGRJwR+ABV8VQzudgjiAGrLCUAdRFIDZZ0FaQAShyqGDWqiQGDVcSqJKhjLDbL6SArq0pmRLFYQIRaLgEghuiAYBB6DhdCAAFYKWhIKi4RjhBSaGy6GBofgOyxAA?clientId=icc"
                ),
            },
            {
                "name": "Cayenne S E-Hybrid",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/9YABN1"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/9YABN1/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQFV6AIwwBZNGAYciCKylDEqJZU-IgAFvhQSKggbBwAIgCCAJrBoQThzFEgCuKsAK5gLiluIACcWRkAQgByAIy5SvkRoJBlzvQAngDCEAYc7gDKwVijtPxZtJooAEwADMsAbPKdKsgkIKsAisGtaQAcJwDiF1TLQwDswcsAWgASwQDMAGIZwQAsXw2-0Oxyof3cjWCAFZ7gAFaG+X5UKEADRRwQ2AEkPhiANK1DHNUEge6rdFUe4fACiwXuKKhtKy7SoZw+aWCZwmABlgrVYY8qBlmsEvgAVHFUS6tS7BTEANWWsoA6hKQLjGkCqFzLqK0gAlHlUZoAKUVVEOrSRIEOeoJVDlQzNIDlSuZIGerSmZEsVhAhFouASCG6IBgEHoOF0IAAVgpaEgqLhGOEFJobLoYGh+P7LEA?clientId=icc"
                ),
            },
            {
                "name": "Cayenne S E-Hybrid Black Edition",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/9YAEN1"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/WW/9YAEN1/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQFV6AIwwBZNGAYciCKylDEqJZU-IgAFvhQSKggbBwAIgCCAJrBoQThzFEgCuKsAK5gLiluIACcWRkAogByAIy5SvkRoJBlzvQAngDCEAYcAOrjwVijtPxZtJooAEwADMsAbPKdKsgkIKuNwa1pAOzHACoAzMFXGe1UACwAYsvBAKynAIofABpDwQ2AEkblQNgBpWqA5oAKWCpw2AKopwy4Phv3ewQAHFcAELBDIANWCjV8oJAz2uwQA4q1qcEgeNyTDGuSADLUi5pABKbOCX2WcKoX25UOFhJuZEsVhAhFouASCG6IBgEHoOF0IAAVgpaEgqLhGOEFJobLoYGh+HLLEA?clientId=icc"
                ),
            },
            {
                "name": "Cayenne GTS",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/9YABS1"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/9YABS1/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQFV6AIwwBZNGAYciCKylDEqJZU-IgAFvhQSKggbBwAIgCCAJrBoQThzFEgCuKsAK5gLiluIACcWRkAQgDKAIy5SvkRoJBlzvQAngDCEAYc7s3BWKO0-Fm0migATAAMSwBs8p0qyCQgKwAywa1pABzHAOLrwUtDAOzBAMwAYhnBACzP11TvAIq-H3cjWCAFY7gAlUEADShwXWAElHnCANK1OEAOUmVDuUJBwTuWXaVFOjwAosFTs14cFagAFB5UZ4AFSRVAurQuwQuQ2C8IAakteQB1VkgA4XJlpcFHKi-E7BX7gtFUPlDQUqoVEkAALVakzIlisIEItFwCQQ3RAMAg9BwuhAACsFLQkFRcIxwgpNDZdDA0PwTZYgA?clientId=icc"
                ),
            },
            {
                "name": "Cayenne Turbo E-Hybrid",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/9YACT1"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/9YACT1/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQFV6AIwwBZNGAYciCKylDEqJZU-IgAFvhQSKggbBwAIgCCAJrBoQThzFEgCuKsAK5gLiluIACcWRkAwgAqAIy5SvkRoJBlzvQAno0QBhzuAMrBWCO0-Fm0migATAAMSwBs8p0qyCQgKwCiwa1pABzHAOLnVADMAGIZwQAsd+vPAIrvz+4AQsEArAANQHBdYASRuoIA0rVQQA5SZUADsKxByJuR2RgP+wSRWXaVFOGOCp3GABlgrUAApI4J3ZqQqgXVoXYJggBqSzZAHVGSAoT83lQyRdmmkAEoUqhwgBSXKo71aMuC73FsKo7hu8pA7Ma2vZmJ13IJIAAWq1JmRLFYQIRaLgEghuiAYBB6DhdCAAFYKWhIKi4RjhBSaGy6GBofh2yxAA?clientId=icc"
                ),
            },
            {
                "name": "Cayenne Coupé",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/9YBAI1"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/9YBAI1/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQFV6AIwwBZNGAYciCKylDEqJZU-IgAFvhQSKggbBwAIgCCAJrBoQThzFEgCuKsAK5gLiluIACcWQBCGQCSAIy5SvkRoJBlzvQAngDCEAYc7gDKwVijtPxZtJooAEwADMsAbPKdKsgkIKu+AKzBrWkAHKcA4hunAFq+wctDAOxPdwASwQAsAMwAoj8AGK3KjfACK4J+7gawSOAA14cENs1fsiANK1ZEAOShVBe8JO+Ky7So51+aWC5wmABlgrUAApvKgZbHBIEAFTRVCurSuwWaRJAzQAassBQB1bkgGlXDlpABKdKo4LOwXBCqxVBFQ3F2olpJAd1aUzIlisIEItFwCQQ3RAMAg9BwuhAACsFLQkFRcIxwgpNDZdDA0PwrZYgA?clientId=icc"
                ),
            },
            {
                "name": "Cayenne Coupé Black Edition",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/9YBDI1"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/WW/9YBDI1/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQFV6AIwwBZNGAYciCKylDEqJZU-IgAFvhQSKggbBwAIgCCAJrBoQThzFEgCuKsAK5gLiluIACcWQBCaQCSAIy5SvkRoJBlzvQAngDCEAYcAOrjwVijtPxZtJooAEwADMsAbPKdKsgkIKsAosGtaQDsJwAqAMzB1xntVAAsAGLLwQCsZwCKnwAaQ2CG2atyoGwA0rUgQA5ABSwTOGXBCL+H2CAA5rg1ghkAGrBQ6+UEgF43YIAcVa5OCzXGxNhh2JABlyZc0gAlJnBb7LeFUb7sqH83G3MiWKwgQi0XAJBDdEAwCD0HC6EAAKwUtCQVFwjHCCk0Nl0MDQ-ClliAA?clientId=icc"
                ),
            },
            {
                "name": "Cayenne E-Hybrid Coupé",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/9YBAV1"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/9YBAV1/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQFV6AIwwBZNGAYciCKylDEqJZU-IgAFvhQSKggbBwAIgCCAJrBoQThzFEgCuKsAK5gLiluIACcWQBCGQBqAIy5SvkRoJBlzvQAngDCEAYc7gDKwVijtPxZtJooAEwADMsAbPKdKsgkIKsAisGtaQAcJwDiF1StAFrHVMtDAOzBy3cAEsEALABiG1+h0eIB+7gawQArC8AHJQgAa8OCGwAkgBmZEAaVqyJhIJeqyRVBeaIAosEXvDIRSsu0qGc0WlgmcJgAZYK1AAKbyoGThVD+ABUMVRLq1LsEUc1lpKAOoikCYhqAqisy6CtIAJXZVBhACkZVRDqdgodNTiqM0hoaQM1ZXSQHdWlMyJYrCBCLRcAkEN0QDAIPQcLoQAArBS0JBUXCMcIKTQ2XQwND8T2WIA?clientId=icc"
                ),
            },
            {
                "name": "Cayenne E-Hybrid Coupé Black Edition",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/9YBDI1"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/WW/9YBDI1/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQFV6AIwwBZNGAYciCKylDEqJZU-IgAFvhQSKggbBwAIgCCAJrBoQThzFEgCuKsAK5gLiluIACcWQBCaQCSAIy5SvkRoJBlzvQAngDCEAYcAOrjwVijtPxZtJooAEwADMsAbPKdKsgkIKsAosGtaQDsJwAqAMzB1xntVAAsAGLLwQCsZwCKnwAaQ2CG2atyoGwA0rUgQA5ABSwTOGXBCL+H2CAA5rg1ghkAGrBQ6+UEgF43YIAcVa5OCzXGxNhh2JABlyZc0gAlJnBb7LeFUb7sqH83G3MiWKwgQi0XAJBDdEAwCD0HC6EAAKwUtCQVFwjHCCk0Nl0MDQ-ClliAA?clientId=icc"
                ),
            },
            {
                "name": "Cayenne S Coupé",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/9YBBJ1"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/9YBBJ1/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQFV6AIwwBZNGAYciCKylDEqJZU-IgAFvhQSKggbBwAIgCCAJrBoQThzFEgCuKsAK5gLiluIACcWQBCDQBSAIy5SvkRoJBlzvQAngDCEAYc7gDKwVijtPxZtJooAEwADMsAbPKdKsgkIK1pABzBrQDiG6cAWkPBy0MA7HdXABLBACwAYpdU7wCKfw+7gawQArL4MmCABpQ4IbACSAGY4QBpWpwgBygKoDyhoOCDyy7SoR0RaWCRwmABlgrUAApPKgZDHBT4AFWRVDO52C8PxVHhADVlryAOqckBUs5stIAJRpVD+h2Cf1l6KowolgqGIo1ouJICurSmZEsVhAhFouASCG6IBgEHoOF0IAAVgpaEgqLhGOEFJobLoYGh+JbLEA?clientId=icc"
                ),
            },
            {
                "name": "Cayenne S E-Hybrid Coupé",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/9YBBN1"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/9YBBN1/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQFV6AIwwBZNGAYciCKylDEqJZU-IgAFvhQSKggbBwAIgCCAJrBoQThzFEgCuKsAK5gLiluIACcWQBCDQByAIy5SvkRoJBlzvQAngDCEAYc7gDKwVijtPxZtJooAEwADMsAbPKdKsgkIKsAisGtaQAcJwDiF1TLQwDswcsAWgASwQAsAGIbn4fHVA+7gawQArL4MmCABpQ4IbACSAGY4QBpWpw5oAkD3Vawqj3REAUWC9yhoJJWXaVDOiLSwTOEwAMsFagAFR5UDLNYJfAAqyKol1al2C8IAastRQB1AUgFENX5URmXXlpABKzKozQAUpKqIdTsFDmr0VQJbKxUM9SAxVKqSBnq0pmRLFYQIRaLgEghuiAYBB6DhdCAAFYKWhIKi4RjhBSaGy6GBofgeyxAA?clientId=icc"
                ),
            },
            {
                "name": "Cayenne S E-Hybrid Coupé Black Edition",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/9YBEN1"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/9YBBN1/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQFV6AIwwBZNGAYciCKylDEqJZU-IgAFvhQSKggbBwAIgCCAJrBoQThzFEgCuKsAK5gLiluIACcWQBCDQByAIy5SvkRoJBlzvQAngDCEAYc7gDKwVijtPxZtJooAEwADMsAbPKdKsgkIKsAisGtaQAcJwDiF1TLQwDswcsAWgASwQAsAGIbn4fHVA+7gawQArL4MmCABpQ4IbACSAGY4QBpWpw5oAkD3Vawqj3REAUWC9yhoJJWXaVDOiLSwTOEwAMsFagAFR5UDLNYJfAAqyKol1al2C8IAastRQB1AUgFENX5URmXXlpABKzKozQAUpKqIdTsFDmr0VQJbKxUM9SAxVKqSBnq0pmRLFYQIRaLgEghuiAYBB6DhdCAAFYKWhIKi4RjhBSaGy6GBofgeyxAA?clientId=icc"
                ),
            },
            {
                "name": "Cayenne GTS Coupe",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/9YBBS1"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/9YBBS1/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQFV6AIwwBZNGAYciCKylDEqJZU-IgAFvhQSKggbBwAIgCCAJrBoQThzFEgCuKsAK5gLiluIACcWQBCDQDKAIy5SvkRoJBlzvQAngDCEAYc7s3BWKO0-Fm0migATAAMSwBs8p0qyCQgKwAywa1pABzHAOLrwUtDAOzBACwAYtdUjwCKH0-uDcEArHcAEoAgAaoOC6wAkgBmSEAaVqkIAcpMqHdQf9gncsu0qKcYQBRYKnZpQ4K1AAKDyozwAKnCqBdWhdghchsEoQA1JacgDqjJABwudLSQKOVA+J2CHyBSKoXKGvIVfLxIAAWq1JmRLFYQIRaLgEghuiAYBB6DhdCAAFYKWhIKi4RjhBSaGy6GBofgGyxAA?clientId=icc"
                ),
            },
            {
                "name": "Cayenne Turbo E-Hybrid Coupe",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/9YBCT1"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/9YBCT1/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQFV6AIwwBZNGAYciCKylDEqJZU-IgAFvhQSKggbBwAIgCCAJrBoQThzFEgCuKsAK5gLiluIACcWQBCAMIAKgCMuUr5EaCQZc70AJ5NEAYc7gDKwVijtPxZtJooAEwADMsAbPJdKsgkIKsAosFtaQAcJwDiF1QALABiG8G3AIovz+4NwQCsABq-wQ2AEkAMyAgDStUBADkplQAOyrAEIkHHBG-b7BeFZDpUM6o4JnCYAGWCtQACvDgvcWmCqJc2pdgkCAGrLZkAdTpIHBDSeVGJlxaaQASqSqNCAFLsqgvNqS4IvEVQqjuEEykAspoallozUc3EgABabSmZEsVhAhFouASCB6IBgEHoOF0IAAVgpaEgqLhGOEFJobLoYGh+NbLEA?clientId=icc"
                ),
            },
            {
                "name": "Cayenne Turbo E-Hybrid Coupé with GT Package",
                "link": (
                    "https://configurator.porsche.com/en-WW/mode/model/9YBCZ1"
                ),
                "price": "null",
                "image": (
                    "https://prs.porsche.com/iod/image/US/9YBCP1/1/N4Igxg9gdgZglgcxALlAQynAtmgLnaAZxQG0BdAGnDSwFMAnNFUOAExRFoA9cBaAGwgB3XjHrQ+-WjFwgqEAA74izEADc09OBlnIQrWoQDWuRSAC+5qrShq44qHSi6W7PQHU4UVgBUArlBQtPxyIIrKUMSollT8iAAW+FBIqCBsHAAiAIIAmqHhBJHMMSAK4qx+YC5pbiAAnDkAQgDCAAoAjPlKhVGgkAG49ACezRAGHACqAMqhWGPBObSaKABMAAwrAGzy3SrIJCDtAOKboe0AEqEAzAAsoTcA7ABK9wBip1Q3AIpf9xONoQArAANYGhTYASSu4IA0nVwQA5GZUB7AwGhB45TpUAAcUwAMqE6q0HqFXj5oVQjsdQhCAGorWnuSkgfFHHwZJ6EqhfdoZUJfJ7wqh05qMkXubEgABa7RmZEsVhAhFouCSCF6IBgEHoOF0IAAVgpaEgqIMMIQFJobLoYGh+CrLEA?clientId=icc"
                ),
            }
        ],
    }
}

# ══════════════════════════════════════════════════════════════════════════════
#  SECTION REGISTRY
# ══════════════════════════════════════════════════════════════════════════════
SECTIONS = [
    {
        "key": "exterior_colors",
        "btn_testid": "section-section-exterior-color-button",
        "container_id": "section-exterior-color-toggle-container",
        "strategy": "flat_with_expand",
    },
    {
        "key": "wheels",
        "btn_testid": "section-section-wheels-button",
        "container_id": "section-wheels-toggle-container",
        "strategy": "wheels",
    },
    {
        "key": "interior_colors_and_material",
        "btn_testid": "section-section-interior-color-button",
        "container_id": "section-interior-color-toggle-container",
        "strategy": "interior_colors",
    },
    {
        "key": "seats",
        "btn_testid": "section-section-interior-seats-button",
        "container_id": "section-interior-seats-toggle-container",
        "strategy": "flat",
    },
    {
        "key": "packages",
        "btn_testid": "section-section-individualization-packages-button",
        "container_id": "section-individualization-packages-toggle-container",
        "strategy": "flat",
    },
    {
        "key": "exterior",
        "btn_testid": "section-section-individualization-exterior-button",
        "container_id": "section-individualization-exterior-toggle-container",
        "strategy": "toggle_subcats",
    },
    {
        "key": "interior",
        "btn_testid": "section-section-individualization-interior-button",
        "container_id": "section-individualization-interior-toggle-container",
        "strategy": "interior",
    },
    {
        "key": "technology",
        "btn_testid": "section-section-individualization-technology-button",
        "container_id": "section-individualization-technology-toggle-container",
        "strategy": "toggle_subcats",
    },
    {
        "key": "vehicle_accessories",
        "btn_testid": "section-section-vehicle-accessories-button",
        "container_id": "section-vehicle-accessories-toggle-container",
        "strategy": "toggle_subcats",
    },
    {
        "key": "delivery_experience",
        "btn_testid": "section-section-individualization-delivery-button",
        "container_id": "section-individualization-delivery-toggle-container",
        "strategy": "flat",
    },
]


# ══════════════════════════════════════════════════════════════════════════════
#  DRIVER FACTORY
# ══════════════════════════════════════════════════════════════════════════════
def build_driver(headless=False):
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    if USE_WDM:
        driver = webdriver.Chrome(
            service=ChromeService(ChromeDriverManager().install()), options=opts
        )
    else:
        driver = webdriver.Chrome(options=opts)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"},
    )
    return driver


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def safe_click(driver, el):
    driver.execute_script("arguments[0].scrollIntoView({block:'center',inline:'center'});", el)
    time.sleep(0.5)
    try:
        el.click()
    except ElementClickInterceptedException:
        driver.execute_script("arguments[0].click();", el)


def dismiss_overlays(driver, timeout=15):
    """
    Wait for and click the cookie 'Accept all' button.

    The Porsche site uses Usercentrics which renders the consent dialog as a
    chain of nested custom elements / shadow roots:

        #usercentrics-root  (shadow host in main document)
          └─ shadow-root
               └─ ... deeper shadow hosts ...
                    └─ <uc-p-button class="accept" variant="primary">
                         └─ shadow-root
                              └─ <button>Accept all</button>

    Strategy (4 tiers, tried in order until one succeeds):
      1. Poll up to `timeout` seconds: walk ALL shadow roots recursively in JS
         and click the inner <button> inside uc-p-button.
      2. Direct CSS on uc-p-button in the main DOM (if not deeply nested).
      3. Switch into every iframe and repeat the shadow-walk there.
      4. XPath text-content fallback for any visible 'Accept all' element.
    """
    log.info("Waiting for cookie banner (up to %ds)...", timeout)

    JS_SHADOW_CLICK = """
        function deepQuery(root, selector) {
            var queue = [root];
            while (queue.length) {
                var node = queue.shift();
                var found = node.querySelectorAll(selector);
                if (found.length) return Array.from(found);
                var all = node.querySelectorAll('*');
                for (var i = 0; i < all.length; i++) {
                    if (all[i].shadowRoot) queue.push(all[i].shadowRoot);
                }
            }
            return [];
        }

        var buttons = deepQuery(document, 'uc-p-button.accept');
        if (!buttons.length) {
            buttons = deepQuery(document, 'uc-p-button[variant="primary"]');
        }

        for (var i = 0; i < buttons.length; i++) {
            var host = buttons[i];
            if (host.shadowRoot) {
                var inner = host.shadowRoot.querySelector('button');
                if (inner) { inner.click(); return 'shadow-inner:' + i; }
            }
            host.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
            return 'host-dispatch:' + i;
        }
        return null;
    """

    # ── Tier 1: poll + recursive shadow-DOM walk ──────────────────────────────
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            result = driver.execute_script(JS_SHADOW_CLICK)
            if result:
                time.sleep(1.5)
                log.info("Cookie banner dismissed via shadow-DOM walk (%s)", result)
                return
        except Exception as e:
            log.debug("Shadow-walk attempt error: %s", e)
        time.sleep(0.5)

    log.debug("Shadow-walk timed out after %ds — trying fallback tiers", timeout)

    # ── Tier 2: direct CSS on uc-p-button in main DOM ─────────────────────────
    for sel in [
        "uc-p-button.accept",
        "uc-p-button[variant='primary']",
        "#onetrust-accept-btn-handler",
        "button[data-testid='uc-accept-all-button']",
        "button.accept-all-button",
        "[aria-label*='Accept all']",
        "[aria-label*='accept all']",
    ]:
        try:
            btn = driver.find_element(By.CSS_SELECTOR, sel)
            if btn.is_displayed():
                safe_click(driver, btn)
                time.sleep(1.5)
                log.info("Cookie banner dismissed via CSS selector (%s)", sel)
                return
        except NoSuchElementException:
            pass

    # ── Tier 3: search inside every iframe ────────────────────────────────────
    try:
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for iframe in iframes:
            try:
                driver.switch_to.frame(iframe)
                result = driver.execute_script(JS_SHADOW_CLICK)
                if result:
                    time.sleep(1.5)
                    log.info("Cookie banner dismissed inside iframe via shadow-walk (%s)", result)
                    driver.switch_to.default_content()
                    return
                for sel in ["uc-p-button.accept", "uc-p-button[variant='primary']"]:
                    try:
                        btn = driver.find_element(By.CSS_SELECTOR, sel)
                        if btn.is_displayed():
                            safe_click(driver, btn)
                            time.sleep(1.5)
                            log.info("Cookie banner dismissed in iframe via CSS (%s)", sel)
                            driver.switch_to.default_content()
                            return
                    except NoSuchElementException:
                        pass
            except Exception:
                pass
            finally:
                try:
                    driver.switch_to.default_content()
                except Exception:
                    pass
    except Exception as e:
        log.debug("iframe search failed: %s", e)

    # ── Tier 4: XPath visible text match ──────────────────────────────────────
    try:
        for el in driver.find_elements(
            By.XPATH,
            "//*[normalize-space(.)='Accept all' or normalize-space(text())='Accept all']"
        ):
            try:
                if el.is_displayed():
                    safe_click(driver, el)
                    time.sleep(1.5)
                    log.info("Cookie banner dismissed via XPath text match")
                    return
            except Exception:
                pass
    except Exception as e:
        log.debug("XPath text-match failed: %s", e)

    log.warning("Cookie banner not found or already dismissed — continuing")


def get_hero_image(driver):
    """Improved hero image detection"""
    for sel in [
        "img[src*='prs.porsche.com']",
        "img[src*='/iod/image/']",
        "img[src*='models.porsche.com']",
        "img[src*='pictures.porsche.com']",
        "div[class*='viewer'] img",
        "div[role='img']",
        "[data-testid='stage-image'] img"
    ]:
        try:
            for el in driver.find_elements(By.CSS_SELECTOR, sel):
                src = el.get_attribute("src") or ""
                if src and "data:image" not in src and len(src) > 30:
                    return src
        except Exception:
            pass

    try:
        images = driver.find_elements(By.TAG_NAME, "img")
        for img in images:
            src = img.get_attribute("src") or ""
            if src and "data:image" not in src and len(src) > 50:
                width = img.get_attribute("width") or "0"
                height = img.get_attribute("height") or "0"
                try:
                    if int(width) > 300 or int(height) > 300:
                        return src
                except Exception:
                    if "porsche" in src.lower() and "config" in src.lower():
                        return src
    except Exception:
        pass

    try:
        for canvas in driver.find_elements(By.TAG_NAME, "canvas"):
            w = int(canvas.get_attribute("width") or "0")
            h = int(canvas.get_attribute("height") or "0")
            if w > 300 and h > 200:
                data_url = driver.execute_script("return arguments[0].toDataURL('image/png');", canvas)
                if data_url and data_url.startswith("data:image"):
                    return data_url
    except Exception:
        pass

    return ""


def wait_for_image_change(driver, old_src, timeout=8.0):
    """Improved image change detection with multiple checks"""
    deadline = time.time() + timeout
    time.sleep(0.5)

    while time.time() < deadline:
        new_src = get_hero_image(driver)
        if new_src and new_src != old_src:
            if len(new_src) > 30 and "data:image" not in new_src:
                return new_src
        time.sleep(0.3)

    final_src = get_hero_image(driver)
    if final_src and final_src != old_src:
        return final_src

    return old_src


def extract_price_from_text(text):
    if not text:
        return ""
    m = re.search(r'\$[\d,]+(?:\.\d{2})?', text)
    return m.group(0) if m else ""


def slugify(text):
    """Convert any heading text to a clean snake_case key."""
    return re.sub(r'[^a-z0-9]+', '_', text.lower()).strip('_')


def expand_all_toggle_buttons(driver, container, label="section", max_passes=5):
    """
    Expand ALL collapsed toggle buttons inside a container.
    Works for any section regardless of model-specific category IDs.
    Returns the refreshed container element.
    """
    container_id = container.get_attribute("id") or ""

    for pass_num in range(max_passes):
        if container_id:
            try:
                container = driver.find_element(By.ID, container_id)
            except NoSuchElementException:
                break

        collapsed = container.find_elements(
            By.CSS_SELECTOR,
            "button[aria-expanded='false'][aria-controls$='-toggle-container']",
        )
        if not collapsed:
            log.info(f"    [{label}] All toggles expanded after pass {pass_num + 1}")
            break

        log.info(f"    [{label}] Pass {pass_num + 1}: {len(collapsed)} collapsed button(s)")
        for btn in collapsed:
            try:
                controls = btn.get_attribute("aria-controls") or ""
                try:
                    lbl = btn.find_element(By.CSS_SELECTOR, "h3").text.strip()
                except NoSuchElementException:
                    lbl = btn.text.strip().split("\n")[0] or controls
                log.info(f"      Expanding: '{lbl}' → #{controls}")
                if btn.get_attribute("aria-expanded") != "true":
                    safe_click(driver, btn)
                    time.sleep(1.5)
            except StaleElementReferenceException:
                log.debug("      Button stale, skipping")
            except Exception as e:
                log.debug(f"      Expand failed: {e}")
        time.sleep(1.0)

    time.sleep(2.0)
    if container_id:
        try:
            container = driver.find_element(By.ID, container_id)
        except NoSuchElementException:
            pass
    return container


def get_group_price(driver, input_el, container_el):
    for xpath in [
        "./ancestor::div[.//h3 and .//p[contains(@class,'text-contrast')]][1]",
        "./ancestor::div[.//h3][1]",
    ]:
        try:
            group_block = input_el.find_element(By.XPATH, xpath)
            price_span = group_block.find_element(
                By.CSS_SELECTOR,
                "p.text-contrast-medium span, p[class*='text-contrast'] span, span[class*='price']",
            )
            price = extract_price_from_text(price_span.text)
            if price:
                return price
        except Exception:
            pass
    try:
        group_wrapper = input_el.find_element(
            By.XPATH,
            "./ancestor::div[contains(@class,'flex-col') or contains(@class,'grid')][1]/parent::div",
        )
        price_span = group_wrapper.find_element(By.XPATH, ".//p[contains(@class,'text-contrast')]//span")
        price = extract_price_from_text(price_span.text)
        if price:
            return price
    except Exception:
        pass
    try:
        all_spans = container_el.find_elements(
            By.CSS_SELECTOR, "p.text-contrast-medium span, p[class*='text-contrast'] span"
        )
        result = driver.execute_script("""
            var input = arguments[0]; var spans = arguments[1];
            var inputTop = input.getBoundingClientRect().top;
            var best = null; var bestDist = Infinity;
            for (var i = 0; i < spans.length; i++) {
                var spanTop = spans[i].getBoundingClientRect().top;
                var dist = inputTop - spanTop;
                if (dist >= 0 && dist < bestDist) { bestDist = dist; best = spans[i]; }
            }
            return best ? best.textContent.trim() : '';
        """, input_el, all_spans)
        price = extract_price_from_text(result or "")
        if price:
            return price
    except Exception:
        pass
    return ""


def get_card_price(card_el):
    try:
        span = card_el.find_element(
            By.CSS_SELECTOR,
            "p.text-contrast-medium span, p[class*='text-contrast'] span"
        )
        return extract_price_from_text(span.text)
    except Exception:
        pass
    try:
        price_text = card_el.find_element(
            By.CSS_SELECTOR,
            "label p.text-contrast-medium, label p[class*='text-contrast']"
        ).text
        return extract_price_from_text(price_text)
    except Exception:
        pass
    return ""


def extract_swatch_style(input_el):
    style = input_el.get_attribute("style") or ""
    swatch_image = ""
    swatch_colors = []

    url_match = re.search(r'background-image\s*:\s*url\(["\']?([^"\'\)]+)["\']?\)', style)
    if url_match:
        src = url_match.group(1)
        if src.startswith("//"):
            src = "https:" + src
        elif src.startswith("/"):
            src = "https://configurator.porsche.com" + src
        swatch_image = src
        return {"swatch_image": swatch_image, "swatch_colors": swatch_colors}

    bg_color_match = re.search(r'background-color\s*:\s*(rgb[a]?\([^)]+\))', style)
    if bg_color_match:
        swatch_colors.append(bg_color_match.group(1).strip())
        return {"swatch_image": swatch_image, "swatch_colors": swatch_colors}

    if "linear-gradient" in style:
        rgb_values = re.findall(r'rgb\(\s*[\d,\s]+\)', style)
        seen = set()
        for c in rgb_values:
            normalized = re.sub(r'\s+', '', c)
            if normalized not in seen:
                seen.add(normalized)
                swatch_colors.append(c.strip())

    return {"swatch_image": swatch_image, "swatch_colors": swatch_colors}


# ══════════════════════════════════════════════════════════════════════════════
#  ATOMIC SCRAPERS
# ══════════════════════════════════════════════════════════════════════════════
def capture_image_on_click(driver, click_target, option_name):
    """Helper function to reliably capture image after click"""
    car_image = ""
    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center', behavior: 'smooth'});", click_target)
        time.sleep(0.8)

        before_image = get_hero_image(driver)

        try:
            click_target.click()
        except Exception:
            driver.execute_script("arguments[0].click();", click_target)

        time.sleep(1.5)

        car_image = wait_for_image_change(driver, before_image, timeout=10.0)

        if not car_image or car_image == before_image:
            time.sleep(2.0)
            car_image = get_hero_image(driver)

    except Exception as e:
        log.debug(f"        image capture failed for '{option_name}': {e}")
        car_image = get_hero_image(driver)

    return car_image


def scrape_swatch_options(driver, container_el):
    options = []
    color_inputs = container_el.find_elements(
        By.CSS_SELECTOR,
        "input[type='checkbox'][style*='background-image'], "
        "input[type='radio'][style*='background-image'], "
        "input[type='checkbox'][style*='background-color'], "
        "input[type='radio'][style*='background-color']",
    )
    if not color_inputs:
        return options
    log.info(f"        found {len(color_inputs)} swatch inputs")
    for idx, input_el in enumerate(color_inputs):
        try:
            label = None
            input_id = input_el.get_attribute("id")
            if input_id:
                try:
                    label = container_el.find_element(By.CSS_SELECTOR, f"label[for='{input_id}']")
                except NoSuchElementException:
                    pass
            if not label:
                try:
                    label = input_el.find_element(By.XPATH, "./ancestor::label[1]")
                except NoSuchElementException:
                    pass

            name = input_el.get_attribute("aria-label") or ""
            if not name and label:
                name = label.get_attribute("aria-label") or label.text.strip()
            if not name:
                name = input_el.get_attribute("value") or f"Option_{idx}"

            price = get_group_price(driver, input_el, container_el)
            if not price and label:
                price = extract_price_from_text(label.text)

            swatch_data = extract_swatch_style(input_el)
            is_selected = input_el.is_selected() or input_el.get_attribute("checked") == "true"

            car_image = ""
            click_target = label if label else input_el
            is_exterior = "exterior" in str(container_el.get_attribute("id")).lower()

            if is_exterior and click_target and click_target.is_enabled():
                car_image = capture_image_on_click(driver, click_target, name)

            options.append({
                "name": name,
                "price": price,
                "swatch_image": swatch_data["swatch_image"],
                "swatch_colors": swatch_data["swatch_colors"],
                "car_image": car_image,
                "currently_selected": is_selected,
            })
            log.info(
                "        ✓ [%d/%d] %-40s price=%-12s colors=%d img=%s",
                idx+1, len(color_inputs), name[:40], price or "—",
                len(swatch_data["swatch_colors"]),
                "✓" if car_image else "✗",
            )
        except Exception as e:
            log.debug(f"        error processing swatch {idx}: {e}")
    return options


def scrape_card_options(driver, container_el):
    options = []
    card_wrappers = container_el.find_elements(
        By.CSS_SELECTOR,
        "div.overflow-hidden.rounded-md, div[class*='overflow-hidden'][class*='rounded']"
    )
    if not card_wrappers:
        card_wrappers = container_el.find_elements(
            By.CSS_SELECTOR,
            "div[class*='border-surface'][class*='rounded-md'], "
            "div[class*='border-surface'][class*='rounded']"
        )
    if not card_wrappers:
        return options

    log.info(f"        found {len(card_wrappers)} card options")
    for idx, card in enumerate(card_wrappers):
        try:
            name = ""
            swatch_image = ""

            try:
                info_a = card.find_element(By.CSS_SELECTOR, "a[aria-label][aria-haspopup='dialog']")
                raw = info_a.get_attribute("aria-label") or ""
                candidate = re.sub(r"^Show more information about\s+", "", raw).strip()
                if candidate:
                    name = candidate
            except NoSuchElementException:
                pass

            if not name:
                try:
                    inp = card.find_element(By.CSS_SELECTOR, "input[type='checkbox'], input[type='radio']")
                    name = inp.get_attribute("aria-label") or ""
                except NoSuchElementException:
                    pass

            if not name:
                try:
                    name = card.find_element(By.CSS_SELECTOR, "img").get_attribute("alt") or ""
                except NoSuchElementException:
                    pass

            if not name:
                try:
                    name = card.find_element(By.CSS_SELECTOR, "label p").text.strip()
                except NoSuchElementException:
                    pass

            if not name:
                name = f"Option_{idx}"

            price = get_card_price(card)

            try:
                src = card.find_element(By.CSS_SELECTOR, "img").get_attribute("src") or ""
                if src and not src.startswith("data:"):
                    swatch_image = (
                        "https://configurator.porsche.com" + src
                        if src.startswith("/") else src
                    )
            except NoSuchElementException:
                pass

            input_el = None
            label_el = None
            is_selected = False
            try:
                input_el = card.find_element(By.CSS_SELECTOR, "input[type='checkbox'], input[type='radio']")
                chk = input_el.get_attribute("checked")
                is_selected = input_el.is_selected() or (chk is not None and chk != "false")
                label_el = card.find_element(By.CSS_SELECTOR, "label")
            except NoSuchElementException:
                pass

            click_target = label_el or input_el

            car_image = ""
            is_exterior = "exterior" in str(container_el.get_attribute("id")).lower()

            if is_exterior and click_target and click_target.is_enabled():
                car_image = capture_image_on_click(driver, click_target, name)

            options.append({
                "name": name,
                "price": price,
                "swatch_image": swatch_image,
                "swatch_colors": [],
                "car_image": car_image,
                "currently_selected": is_selected,
            })
            log.info(
                "        ✓ [%d/%d] %-45s price=%-12s img=%s",
                idx+1, len(card_wrappers), name[:45], price or "—",
                "✓" if car_image else "✗",
            )
        except Exception as e:
            log.debug(f"        error processing card {idx}: {e}")
    return options


def scrape_wheel_items(driver, container_el):
    options = []
    item_divs = container_el.find_elements(By.CSS_SELECTOR, "div[id*='_item-']")
    if not item_divs:
        return options
    log.info(f"        found {len(item_divs)} wheel item divs")
    for idx, item_div in enumerate(item_divs):
        try:
            name = ""
            swatch_image = ""

            try:
                img = item_div.find_element(By.CSS_SELECTOR, "img")
                name = img.get_attribute("alt") or ""
                src = img.get_attribute("src") or ""
                if src and not src.startswith("data:"):
                    swatch_image = (
                        "https://configurator.porsche.com" + src
                        if src.startswith("/") else src
                    )
            except NoSuchElementException:
                pass
            if not name:
                try:
                    inp = item_div.find_element(By.CSS_SELECTOR, "input")
                    name = inp.get_attribute("aria-label") or ""
                except NoSuchElementException:
                    pass
            if not name:
                name = f"Option_{idx}"

            price = get_card_price(item_div)
            if not price:
                price = get_group_price(driver, item_div, container_el)

            is_selected = False
            try:
                inp = item_div.find_element(By.CSS_SELECTOR, "input")
                chk = inp.get_attribute("checked")
                is_selected = inp.is_selected() or (chk is not None and chk != "false")
            except NoSuchElementException:
                pass

            car_image = ""

            options.append({
                "name": name,
                "price": price,
                "swatch_image": swatch_image,
                "swatch_colors": [],
                "car_image": car_image,
                "currently_selected": is_selected,
            })
            log.info(
                "        ✓ [%d/%d] %-45s price=%-12s",
                idx+1, len(item_divs), name[:45], price or "—",
            )
        except Exception as e:
            log.debug(f"        error processing wheel item {idx}: {e}")
    return options


def scrape_label_options(driver, container_el):
    options = []
    option_labels = container_el.find_elements(
        By.CSS_SELECTOR,
        "label[class*='cursor-pointer'], div[class*='cursor-pointer'][role='option'], div[role='radio']",
    )
    if not option_labels:
        return options
    log.info(f"        found {len(option_labels)} label options (fallback)")
    for idx, label in enumerate(option_labels):
        try:
            input_el = None
            for_attr = label.get_attribute("for")
            if for_attr:
                try:
                    input_el = container_el.find_element(By.ID, for_attr)
                except NoSuchElementException:
                    pass
            if not input_el:
                try:
                    input_el = label.find_element(By.CSS_SELECTOR, "input[type='checkbox'], input[type='radio']")
                except NoSuchElementException:
                    pass
            name = label.get_attribute("aria-label") or label.text.strip().split("\n")[0]
            name = re.sub(r"\$[\d,]+.*$", "", name).strip()
            if not name and input_el:
                name = input_el.get_attribute("aria-label") or ""
            if not name:
                continue
            price = ""
            if input_el:
                price = get_group_price(driver, input_el, container_el)
            if not price:
                price = extract_price_from_text(label.text)
            swatch_image = ""
            swatch_colors = []
            if input_el:
                swatch_data = extract_swatch_style(input_el)
                swatch_image = swatch_data["swatch_image"]
                swatch_colors = swatch_data["swatch_colors"]
            is_selected = False
            if input_el:
                is_selected = input_el.is_selected() or input_el.get_attribute("checked") == "true"

            car_image = ""
            is_exterior = "exterior" in str(container_el.get_attribute("id")).lower()

            if is_exterior and label.is_enabled():
                car_image = capture_image_on_click(driver, label, name)

            options.append({
                "name": name,
                "price": price,
                "swatch_image": swatch_image,
                "swatch_colors": swatch_colors,
                "car_image": car_image,
                "currently_selected": is_selected,
            })
            log.info(
                "        ✓ [%d/%d] %-40s price=%-12s img=%s",
                idx+1, len(option_labels), name[:40], price or "—",
                "✓" if car_image else "✗",
            )
        except Exception as e:
            log.debug(f"        error processing label {idx}: {e}")
    return options


def scrape_best(driver, container_el):
    """Cascade through all scrapers, return first non-empty result."""
    for fn in [scrape_swatch_options, scrape_card_options, scrape_wheel_items, scrape_label_options]:
        result = fn(driver, container_el)
        if result:
            return result
    return []


# ══════════════════════════════════════════════════════════════════════════════
#  DYNAMIC SUBCATEGORY DISCOVERY
# ══════════════════════════════════════════════════════════════════════════════
def discover_and_scrape_toggle_subcats(driver, container, section_label="section"):
    result = {}
    seen_toggle_ids = set()

    toggle_btns = container.find_elements(
        By.CSS_SELECTOR,
        "button[aria-controls$='-toggle-container']",
    )
    log.info(f"    [{section_label}] Found {len(toggle_btns)} toggle buttons")

    for btn in toggle_btns:
        controls = btn.get_attribute("aria-controls") or ""
        if not controls or controls in seen_toggle_ids:
            continue
        seen_toggle_ids.add(controls)

        lbl = ""
        try:
            lbl = btn.find_element(By.CSS_SELECTOR, "h3").text.strip()
        except NoSuchElementException:
            pass
        if not lbl:
            cat_id = controls.replace("-toggle-container", "")
            try:
                cat_div = container.find_element(By.ID, f"category-{cat_id}")
                lbl = cat_div.find_element(By.CSS_SELECTOR, "h3").text.strip()
            except NoSuchElementException:
                pass
        if not lbl:
            lbl = btn.text.strip().split("\n")[0].strip()
        if not lbl:
            lbl = controls.replace("-toggle-container", "")

        key = slugify(lbl)
        log.info(f"      ── Toggle subcat: '{lbl}' (#{controls}) key='{key}' ──")

        try:
            toggle_el = driver.find_element(By.ID, controls)
        except NoSuchElementException:
            log.warning(f"      Toggle container #{controls} not found — skipping '{lbl}'")
            result[key] = []
            continue

        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", toggle_el)
        time.sleep(0.5)

        options = scrape_card_options(driver, toggle_el)
        if not options:
            options = scrape_wheel_items(driver, toggle_el)
        if not options:
            options = scrape_swatch_options(driver, toggle_el)
        if not options:
            options = scrape_label_options(driver, toggle_el)

        log.info(f"      → {len(options)} option(s) scraped for '{lbl}'")
        result[key] = options

    return result


def discover_and_scrape_inline_subcats(driver, container, section_label="section"):
    result = {}
    seen_keys = set()

    top_category_divs = container.find_elements(
        By.XPATH,
        ".//div[starts-with(@id,'category-') "
        "and not(contains(@id,'_group-')) "
        "and not(contains(@id,'_item-'))]",
    )

    for cat_div in top_category_divs:
        is_inside_toggle = driver.execute_script("""
            var el = arguments[0];
            while (el.parentElement) {
                el = el.parentElement;
                if ((el.id || '').endsWith('-toggle-container')) return true;
            }
            return false;
        """, cat_div)
        if is_inside_toggle:
            continue

        cat_id_attr = cat_div.get_attribute("id")
        log.info(f"      Inspecting inline category: #{cat_id_attr}")

        flex_blocks = cat_div.find_elements(By.CSS_SELECTOR, "div.flex-col, div[class*='flex-col']")
        found_any = False

        for block in flex_blocks:
            try:
                h3 = block.find_element(By.CSS_SELECTOR, "h3")
                heading = h3.text.strip()
            except NoSuchElementException:
                continue
            if not heading:
                continue

            items = block.find_elements(
                By.CSS_SELECTOR,
                "input[type='checkbox'], input[type='radio'], div[id*='_item-']",
            )
            if not items:
                continue

            key = slugify(heading)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            found_any = True

            log.info(f"      ── Inline subcat: '{heading}' ({len(items)} items) key='{key}' ──")

            options = scrape_swatch_options(driver, block)
            if not options:
                options = scrape_card_options(driver, block)
            if not options:
                options = scrape_wheel_items(driver, block)
            if not options:
                options = scrape_label_options(driver, block)

            log.info(f"      → {len(options)} option(s) scraped for '{heading}'")
            result[key] = options

        if not found_any:
            try:
                heading = cat_div.find_element(By.CSS_SELECTOR, "h3").text.strip()
            except NoSuchElementException:
                heading = cat_id_attr or ""

            if heading:
                key = slugify(heading)
                if key not in seen_keys:
                    seen_keys.add(key)
                    log.info(f"      ── Inline cat (flat): '{heading}' key='{key}' ──")
                    options = scrape_best(driver, cat_div)
                    log.info(f"      → {len(options)} option(s) scraped for '{heading}'")
                    result[key] = options

    return result


# ══════════════════════════════════════════════════════════════════════════════
#  STRATEGY IMPLEMENTATIONS
# ══════════════════════════════════════════════════════════════════════════════
def strategy_flat(driver, container_id, section_key=""):
    try:
        container = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, container_id))
        )
        time.sleep(1)
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", container)
        time.sleep(1)
        return scrape_best(driver, container)
    except TimeoutException:
        log.warning(f"    Container #{container_id} not found")
        return []


def strategy_flat_with_expand(driver, container_id, section_key=""):
    try:
        container = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, container_id))
        )
        time.sleep(1)
        log.info("    Expanding all nested sub-sections...")
        container = expand_all_toggle_buttons(driver, container, label=section_key)
        time.sleep(1.5)
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", container)
        time.sleep(1)
        return scrape_best(driver, container)
    except TimeoutException:
        log.warning(f"    Container #{container_id} not found")
        return []


def strategy_toggle_subcats(driver, container_id, section_key=""):
    result = {}

    try:
        container = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, container_id))
        )
    except TimeoutException:
        log.warning(f"    [{section_key}] Container #{container_id} not found")
        return result

    time.sleep(1)

    log.info(f"    [{section_key}] Step 1: expanding all collapsed toggles...")
    container = expand_all_toggle_buttons(driver, container, label=section_key)

    log.info(f"    [{section_key}] Step 2: scraping inline sub-categories...")
    inline_result = discover_and_scrape_inline_subcats(driver, container, section_label=section_key)
    result.update(inline_result)

    log.info(f"    [{section_key}] Step 3: scraping toggle sub-categories...")
    toggle_result = discover_and_scrape_toggle_subcats(driver, container, section_label=section_key)
    result.update(toggle_result)

    if not result:
        log.warning(f"    [{section_key}] No sub-categories found — falling back to flat scrape")
        result["all"] = scrape_best(driver, container)

    return result


def strategy_wheels(driver, container_id, section_key="wheels"):
    result = {}

    try:
        container = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, container_id))
        )
    except TimeoutException:
        log.warning(f"    [{section_key}] Container #{container_id} not found")
        return result

    time.sleep(1)

    log.info(f"    [{section_key}] Step 1: expanding all toggle sub-sections...")
    container = expand_all_toggle_buttons(driver, container, label=section_key)

    log.info(f"    [{section_key}] Step 2: scraping inline wheel categories (any model)...")
    seen_keys = set()

    top_category_divs = container.find_elements(
        By.XPATH,
        ".//div[starts-with(@id,'category-') "
        "and not(contains(@id,'_group-')) "
        "and not(contains(@id,'_item-'))]",
    )

    for cat_div in top_category_divs:
        is_inside_toggle = driver.execute_script("""
            var el = arguments[0];
            while (el.parentElement) {
                el = el.parentElement;
                if ((el.id || '').endsWith('-toggle-container')) return true;
            }
            return false;
        """, cat_div)
        if is_inside_toggle:
            continue

        flex_blocks = cat_div.find_elements(By.CSS_SELECTOR, "div.flex-col, div[class*='flex-col']")
        found_any = False

        for block in flex_blocks:
            try:
                h3 = block.find_element(By.CSS_SELECTOR, "h3")
                heading = h3.text.strip()
            except NoSuchElementException:
                continue
            if not heading:
                continue

            items = block.find_elements(By.CSS_SELECTOR, "div[id*='_item-']")
            if not items:
                continue

            key = slugify(heading)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            found_any = True

            log.info(f"      ── Inline wheel group: '{heading}' ({len(items)} items) ──")

            options = scrape_wheel_items(driver, block)

            if options and not any(o["price"] for o in options):
                group_price = ""
                try:
                    parent = block.find_element(By.XPATH, "./parent::div")
                    for pd in parent.find_elements(
                        By.CSS_SELECTOR, "p.text-contrast-medium span, p[class*='text-contrast'] span"
                    ):
                        p = extract_price_from_text(pd.text)
                        if p:
                            group_price = p
                            break
                except Exception:
                    pass
                if group_price:
                    for o in options:
                        if not o["price"]:
                            o["price"] = group_price

            log.info(f"      → {len(options)} option(s) scraped for '{heading}'")
            result[key] = options

        if not found_any:
            cat_id_attr = cat_div.get_attribute("id") or ""
            try:
                heading = cat_div.find_element(By.CSS_SELECTOR, "h3").text.strip()
            except NoSuchElementException:
                heading = cat_id_attr

            if heading:
                key = slugify(heading)
                if key not in seen_keys:
                    seen_keys.add(key)
                    log.info(f"      ── Inline cat (flat): '{heading}' ──")
                    options = scrape_wheel_items(driver, cat_div)
                    if not options:
                        options = scrape_best(driver, cat_div)
                    log.info(f"      → {len(options)} option(s) scraped for '{heading}'")
                    result[key] = options

    log.info(f"    [{section_key}] Step 3: scraping toggle sub-sections...")
    toggle_result = discover_and_scrape_toggle_subcats(driver, container, section_label=section_key)
    result.update(toggle_result)

    if not result:
        log.warning(f"    [{section_key}] No wheel data found — flat fallback")
        result["all"] = scrape_best(driver, container)

    return result


def strategy_interior_colors(driver, container_id, section_key="interior_colors_and_material"):
    result = {}

    try:
        container = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, container_id))
        )
    except TimeoutException:
        log.warning(f"    [{section_key}] Container #{container_id} not found")
        return result

    time.sleep(1)
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", container)
    time.sleep(0.5)

    flex_blocks = container.find_elements(By.CSS_SELECTOR, "div.flex-col, div[class*='flex-col']")
    seen_keys = set()
    log.info(f"    [{section_key}] Found {len(flex_blocks)} flex blocks to inspect")

    for block in flex_blocks:
        try:
            h3 = block.find_element(By.CSS_SELECTOR, "h3")
            heading = h3.text.strip()
        except NoSuchElementException:
            continue
        if not heading:
            continue

        key = slugify(heading)
        if key in seen_keys:
            continue

        swatch_inputs = block.find_elements(
            By.CSS_SELECTOR, "input[type='checkbox'][style], input[type='radio'][style]"
        )
        if not swatch_inputs:
            continue

        seen_keys.add(key)

        group_price = ""
        try:
            price_p = block.find_element(
                By.CSS_SELECTOR, "p.text-contrast-medium span, p[class*='text-contrast'] span"
            )
            group_price = extract_price_from_text(price_p.text)
        except NoSuchElementException:
            pass

        log.info(f"      ── Group: '{heading}' ({len(swatch_inputs)} swatches, price={group_price or '—'}) ──")

        options = []
        for idx, input_el in enumerate(swatch_inputs):
            try:
                name = input_el.get_attribute("aria-label") or ""
                if not name:
                    try:
                        ancestor_label = input_el.find_element(By.XPATH, "./ancestor::label[1]")
                        name = ancestor_label.get_attribute("aria-label") or ancestor_label.text.strip()
                    except NoSuchElementException:
                        pass
                if not name:
                    name = input_el.get_attribute("value") or f"Option_{idx}"

                item_price = get_group_price(driver, input_el, block)
                if not item_price:
                    item_price = group_price

                swatch_data = extract_swatch_style(input_el)
                is_selected = (
                    input_el.is_selected() or input_el.get_attribute("checked") == "true"
                )

                click_target = None
                try:
                    click_target = input_el.find_element(By.XPATH, "./ancestor::label[1]")
                except NoSuchElementException:
                    input_id = input_el.get_attribute("id") or ""
                    if input_id:
                        try:
                            click_target = container.find_element(
                                By.CSS_SELECTOR, f"label[for='{input_id}']"
                            )
                        except NoSuchElementException:
                            pass
                if not click_target:
                    click_target = input_el

                car_image = ""

                options.append({
                    "name": name,
                    "price": item_price,
                    "swatch_image": swatch_data["swatch_image"],
                    "swatch_colors": swatch_data["swatch_colors"],
                    "car_image": car_image,
                    "currently_selected": is_selected,
                })
                log.info(
                    "        ✓ [%d/%d] %-45s price=%-10s colors=%d",
                    idx+1, len(swatch_inputs), name[:45], item_price or "—",
                    len(swatch_data["swatch_colors"]),
                )
            except Exception as e:
                log.debug(f"        error processing swatch {idx} in '{heading}': {e}")

        log.info(f"      → {len(options)} option(s) scraped for '{heading}'")
        result[key] = options

    if not result:
        log.warning(f"    [{section_key}] No groups found — falling back to flat scrape")
        result["all"] = scrape_best(driver, container)

    return result


def strategy_interior(driver, container_id, section_key="interior"):
    result = {}

    try:
        container = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, container_id))
        )
    except TimeoutException:
        log.warning(f"    [{section_key}] Container #{container_id} not found")
        return result

    time.sleep(1)

    log.info(f"    [{section_key}] Expanding all sub-categories...")
    container = expand_all_toggle_buttons(driver, container, label=section_key)

    subcat_containers = container.find_elements(By.CSS_SELECTOR, "div[id$='-toggle-container']")
    log.info(f"    [{section_key}] Found {len(subcat_containers)} sub-category containers")

    for subcat_container in subcat_containers:
        try:
            subcat_id = subcat_container.get_attribute("id")
            if not subcat_id or not subcat_id.endswith("-toggle-container"):
                continue
            base_id = subcat_id.replace("-toggle-container", "")

            heading = None
            try:
                category_div = container.find_element(By.CSS_SELECTOR, f"div[id='category-{base_id}']")
                heading = category_div.find_element(By.CSS_SELECTOR, "h3").text.strip()
            except NoSuchElementException:
                pass
            if not heading:
                try:
                    heading = subcat_container.find_element(By.XPATH, "./preceding::h3[1]").text.strip()
                except NoSuchElementException:
                    pass
            if not heading:
                heading = base_id

            key = slugify(heading)
            log.info(f"      ── Sub-category: '{heading}' (#{subcat_id}) key='{key}' ──")

            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", subcat_container)
            time.sleep(0.5)

            options = scrape_card_options(driver, subcat_container)
            if not options:
                options = scrape_best(driver, subcat_container)

            log.info(f"      → {len(options)} option(s) scraped for '{heading}'")
            result[key] = options

        except Exception as e:
            log.debug(f"      Error processing sub-category: {e}")
            continue

    if not result:
        log.warning(f"    [{section_key}] No sub-categories found — falling back to flat scrape")
        result["all"] = scrape_best(driver, container)

    return result


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION DISPATCHER — routes to the right strategy
# ══════════════════════════════════════════════════════════════════════════════
STRATEGY_MAP = {
    "flat":               strategy_flat,
    "flat_with_expand":   strategy_flat_with_expand,
    "toggle_subcats":     strategy_toggle_subcats,
    "wheels":             strategy_wheels,
    "interior_colors":    strategy_interior_colors,
    "interior":           strategy_interior,
}


def expand_section(driver, testid):
    try:
        btn = WebDriverWait(driver, 12).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, f"button[data-testid='{testid}']"))
        )
        if btn.get_attribute("aria-expanded") != "true":
            safe_click(driver, btn)
            time.sleep(2.5)
        log.info("  [✓ open] %s", testid)
        return True
    except TimeoutException:
        log.warning("  [✗ miss] %s – button not found", testid)
        return False


# ══════════════════════════════════════════════════════════════════════════════
#  TRIM SCRAPER
# ══════════════════════════════════════════════════════════════════════════════
def scrape_trim(driver, trim):
    log.info("━" * 60)
    log.info("Loading: %s", trim["link"])
    driver.get(trim["link"])
    time.sleep(5)
    dismiss_overlays(driver)
    time.sleep(2)
    try:
        WebDriverWait(driver, 25).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "button[data-testid='section-section-exterior-color-button']")
            )
        )
        log.info("Page is ready ✓  |  Title: %s", driver.title)
    except TimeoutException:
        log.warning("Timeout waiting for section buttons – proceeding anyway")
        driver.save_screenshot("debug_timeout.png")

    categories = {}

    for section in SECTIONS:
        key          = section["key"]
        testid       = section["btn_testid"]
        container_id = section["container_id"]
        strategy     = section.get("strategy", "flat")

        log.info("")
        log.info("  ── Section: %s  (strategy: %s) ──", key.upper(), strategy)

        opened = expand_section(driver, testid)
        if not opened:
            categories[key] = {} if strategy != "flat" else []
            continue

        scraper_fn = STRATEGY_MAP.get(strategy, strategy_flat)
        categories[key] = scraper_fn(driver, container_id, section_key=key)

    return {
        "name":       trim["name"],
        "base_price": trim["price"],
        "base_image": trim["image"],
        "url":        trim["link"],
        "configurations": [{"configuration_name": "Default Configuration", "categories": categories}],
    }


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    driver = build_driver(headless=False)
    all_models = []

    try:
        for model_name, model_data in CAR_DATA.items():
            log.info("\n" + "═" * 60)
            log.info("  MODEL: %s", model_name)
            log.info("═" * 60)

            scraped_trims = []
            for trim in model_data["trims"]:
                try:
                    scraped = scrape_trim(driver, trim)

                    # Count total options scraped
                    cats = scraped["configurations"][0]["categories"]
                    total = 0
                    for cat_name, cat_val in cats.items():
                        if isinstance(cat_val, dict):
                            for sub_key, sub_val in cat_val.items():
                                c = len(sub_val) if isinstance(sub_val, list) else 0
                                total += c
                        else:
                            total += len(cat_val)
                    log.info("Trim '%s' scraped %d total options", trim["name"], total)

                    scraped_trims.append(scraped)

                    # ── Save individual trim JSON immediately after scraping ──
                    trim_slug = re.sub(r'[^a-z0-9]+', '_', trim["name"].lower()).strip('_')
                    model_slug = re.sub(r'[^a-z0-9]+', '_', model_name.lower()).strip('_')
                    trim_file = f"{model_slug}__{trim_slug}.json"
                    with open(trim_file, "w", encoding="utf-8") as tf:
                        json.dump(scraped, tf, indent=2, ensure_ascii=False)
                    log.info("💾  Trim saved → %s", trim_file)

                except Exception as exc:
                    log.error("Failed to scrape trim '%s': %s", trim["name"], exc)
                    import traceback; traceback.print_exc()

            all_models.append({
                "name": model_name,
                "base_image": model_data["base_image"],
                "trims": scraped_trims,
            })
    finally:
        driver.quit()

    # ── Save combined output for all models ──
    output_file = "porsche_data.json"
    with open(output_file, "w", encoding="utf-8") as fh:
        json.dump(all_models, fh, indent=2, ensure_ascii=False)

    log.info("✅  Scraping complete!  Saved → %s", output_file)
    print("\n" + "═" * 60)
    print(f"  Saved: {output_file}")
    print("═" * 60)
    for m in all_models:
        print(f"\n  Model : {m['name']}")
        for t in m["trims"]:
            print(f"  Trim  : {t['name']}  ({t['base_price']})")
            cats = t["configurations"][0]["categories"]
            total = 0
            for cat_name, cat_val in cats.items():
                if isinstance(cat_val, dict):
                    for sub_key, sub_val in cat_val.items():
                        count = len(sub_val) if isinstance(sub_val, list) else 0
                        total += count
                        print(f"    [{cat_name} → {sub_key}] → {count} options")
                else:
                    count = len(cat_val)
                    total += count
                    print(f"    [{cat_name}] → {count} options")
            print(f"    TOTAL: {total} options")
    print()


if __name__ == "__main__":
    main()
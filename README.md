# Fuzzer Utils
This project requires python3 and AFL.

This project works only on Linux currently.

```
virtualenv -p python3 fu-env
source fu-env/bin/activate
pip install -r requirements.txt
```

You may need to install this in case of error "Tkinter module not found":
```
sudo apt-get install python3-tk
```
# learnopengl.com code repository
Contains python code samples for all tutorials of [http://learnopengl.com](http://learnopengl.com). 

## Windows
All samples were tested on Python27 win64(But should work for other version).

Install all requirement modules with pip
```
pip.exe install -r path_to_LearnPyOpenGL_repo\requirements.txt
```
To run the samples you need to add the pysrc to PYTHONPATH
```
SET PYTHONPATH=%PYTHONPATH%;path_to_LearnPyOpenGL_repo\pysrc
C:\Python27\python.exe path_to_LearnPyOpenGL_repo\pysrc\1.getting_started\2.hellotriangle.py
```

### Using vritrualenv
```
C:\Python27\Scripts\vritrualenv.exe learnPyOpenGL
learnPyOpenGL\Scripts\activate.bat
learnPyOpenGL\Scripts\pip.exe install -r path_to_LearnPyOpenGL_repo\requirements.txt

SET PYTHONPATH=%PYTHONPATH%;path_to_LearnPyOpenGL_repo\pysrc
learnPyOpenGL\Scripts\python.exe path_to_LearnPyOpenGL_repo\pysrc\1.getting_started\2.hellotriangle.py
```

## Linux 
Untest but is should work too. You need to compile assimp and add it to the system's path so pyassimp can find the assimp.so. Or the model loding samples will not work.

## Mac OS X
Same as linux

It might had small bugs.

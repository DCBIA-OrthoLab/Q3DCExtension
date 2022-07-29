# AQ3DC : Automatic Quantification for 3D Cephalometrics

Authors: Baptiste Baquero, Maxime Gillot, Lucia Cevidanes, Jean-Christophe Fillion-Robin, David Allemang
	
## What is it?

This Slicer module aims is to automatically computes head measurements used in craniofacial surgery. Using placed fiducials, it allows users to compute 2D angles: Yaw, Pitch and Roll; and decompose the 3D distance (between points, points to line) into the three different components: R-L , A-P and S-I. It is possible to compute the middle point between two fiducials and export the values. It is possible to compute lists of measurements selected by users for a single case or a whole study sample, at one or more time points.
 
## File Formats

AQ3DC allows users to compute all the measurements on points from .json files. Save middle points created in a .json file. Measurement list and results of all the computed measurements saved as .xlsx files.

## Prerequisites for users

The AQ3DC extension really need consistency in the data. For each patient, in the same time point and at different time point, if the landmarks are not named exactly the same the measurement for this patient won't be perform, and will just be skiped.


## Interface image

![Screenshot from 2022-07-28 11-35-07](https://user-images.githubusercontent.com/83285614/181578776-c87d8b34-7bb7-4bf8-915c-99ba6db2ea4c.png)

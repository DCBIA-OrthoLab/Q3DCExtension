# AQ3DC

Authors: Baptiste Baquero, Maxime Gillot, Lucia Cevidanes, Jean-Christophe Fillion-Robin,David Allemang
	
## What is it?

This Slicer extension aims is to automatically computes lists of measurements selected by users for a single case or a whole study sample, at one or more time points. This user-friendly tool aims to decrease user time for ex-traction of quantitative image analysis features. The AQ3DC implementation is aimed at automatic computation of 3D components of the directionality of distances (Anteroposterior, Right/Left, Supeoinferior) between points, points to line, midpoint between two points or angles (Pitch, Roll and Yaw). Users are able to save in a new file the middle points created. Users will be able to analyze the results of the measurements needed in an excel file. 

## File Formats

AQ3DC allows users to compute all the measurements on points from .json files. Save middle points created in a .json file. Measurement list and results of all the computed measurements saved as .xlsx files.

## Prerequisites for users

The AQ3DC extension really need consistency in the data. For each patient, in the same time point and at different time point, if the landmarks are not named exactly the same the measurement for this patient won't be perform, and will just be skiped.


## Interface image

![Screenshot from 2022-07-28 11-35-07](https://user-images.githubusercontent.com/83285614/181578776-c87d8b34-7bb7-4bf8-915c-99ba6db2ea4c.png)

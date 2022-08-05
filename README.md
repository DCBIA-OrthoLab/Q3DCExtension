# Q3DC

## What is it?

This extension contains one module of the same name. Using placed fiducials, it allows users to compute 2D angles: Yaw, Pitch and Roll; and decompose the 3D distance into the three different components: R-L , A-P and S-I. 
It is possible to compute the middle point between two fiducials and export the values. 

## License

It is covered by the Apache License, Version 2.0:

http://www.apache.org/licenses/LICENSE-2.0

The license file was added at revision 6cc3ad4 on 2020-12-10, but you may consider that the license applies to all prior revisions as well.

## File Formats

Q3DC allows users to define midpoint and projection constraints on points in a Slicer Fiducial list. Saving the Markups with the usual Slicer save dialog will preserve those connections. See [landmarkDescription.md][landmarkDescription] for more information on how MRML attributes are used to do this.

Q3DC also allows users to export computed measurements to CSV files. Note that these files do not encode any of the midpoint and projection constraints as the Markups list does; they only contain the computed measurements in the same tabular format as is displayed in the Q3DC UI.

[landmarkDescription]: ./docs/landmarkDescription.md

# AQ3DC : Automatic Quantification for 3D Cephalometrics

Authors: Baptiste Baquero, Maxime Gillot, Lucia Cevidanes, Jean-Christophe Fillion-Robin, David Allemang
	
## What is it?

This Slicer module's aim is to automatically compute head measurements used in craniofacial surgery. Using placed fiducials, allows users to compute 2D angles: Yaw, Pitch, and Roll; and decompose the 3D distance (between points, points to line) into the three different components: R-L, A-P, and S-I. It is possible to compute the middle point between two fiducials and export the values. It is possible to compute lists of measurements selected by users for a single case or a whole study sample, at one or more time points.

## Difference Q3DC and AQ3DC

The two extensions allow users to compute the same measurements. AQ3DC allows computing the measurement on a whole sample of a patient. Q3DC allows to visualize and interact with the 3D space but only for one patient. So AQ3DC is more useful for users who only want to compute measurements for many patients. Q3DC will be more interactive with the 3D space but not efficient for a huge sample of a patient.
 
## File Formats

AQ3DC allows users to compute all the measurements on points from `.mrk.json` files. Save middle points created in a `.mrk.json` file. Measurement list and results of all the computed measurements saved as `.xlsx` files. See example `.mrk.json` files in [docs/T1](./docs/T1), [docs/T2](./docs/T2)

## Prerequisites for users

The AQ3DC extension requires consistency in data naming. For each patient and time point, the landmark labels must be exactly the same. If an exact match of the expected label name is not found, the measurement will be skipped for that patient with the missing landmark.

## Panels and their use
#### 1. First of all the user needs to provide the folders with all the patients and the landmarks needed for the measurements.
![Folder](https://user-images.githubusercontent.com/83285614/181792321-49e1f513-e42a-4b97-98b5-9bf41d2e2206.jpeg)

#### 2. A table will show up with all the landmarks available in the folders given in T1. Only one table appears if the user doesn't click on the dental tab.
![skeletal_tab](https://user-images.githubusercontent.com/83285614/181792697-1e32c5a6-cc10-494b-853c-6ec38e9d2a53.jpeg)

#### 3. If the user clicks on the dental tab another table with all the teeth of the lower and upper arch pop up on the left of the main table. The landmarks will appear in the landmarks buttons only if the teeth and the type of landmarks associated are selected. 
![dental_tab](https://user-images.githubusercontent.com/83285614/181792711-761cdfb4-d75a-40c6-b774-e377d7c58d5d.jpeg)

#### 4. Midpoints can be added to the main table in a new tab "Midpoint". These new landmarks will be available for measurement and users will be able to save them. If the user is using midpoints in his list of measurements but doesn't save those before, the midpoints will be saved automatically when the user will compute all his measurements.
![midpoint](https://user-images.githubusercontent.com/83285614/181792741-ad084417-af5f-467e-a738-a8c8b128e1a6.jpeg)

#### 5. Table summarizing all the measurements needed. Different modules below the table will appear depending on the tab selected (Distance or Angle).
![measurement_tab](https://user-images.githubusercontent.com/83285614/181792755-13a73d39-db63-4d64-87b0-609183a6e6a5.jpeg)

#### 6. Modules for the different types of distance measurements, depending on the distance type and the time point selected.
![distances](https://user-images.githubusercontent.com/83285614/181795970-d56818fc-604e-4084-80f4-27c3eaaf156e.jpeg)

#### 7. Modules for the different types of angle measurements, depending on the type of the angle and the time point selected.
![angles](https://user-images.githubusercontent.com/83285614/181796000-c653b2b4-9ac7-44ee-b6d2-339e0ee38045.jpeg)

#### 8. Export the measurements table as an excel file, users will be able to use it and modify it if needed for future data samples.
![export](https://user-images.githubusercontent.com/83285614/181792793-fb2f019c-5f0f-4eb4-a843-c711e8348bb6.jpeg)

#### 9. Import an excel file previously build for another study sample.
![import](https://user-images.githubusercontent.com/83285614/181793202-cac70075-06dd-4053-9b55-a1e795e3ef7f.jpeg)

#### 10. Computation part, all the measurements will be computed at one time for all the patients. An excel file with all the results will be created.
![compute](https://user-images.githubusercontent.com/83285614/181792824-c7593417-899e-41d3-802a-7f896aacb983.jpeg)


## Interface image

![Screenshot from 2022-07-28 11-35-07](https://user-images.githubusercontent.com/83285614/181578776-c87d8b34-7bb7-4bf8-915c-99ba6db2ea4c.png)


# History
Q3DC was developed by Lucie Macron (University of Michigan) in 2016 with the contribution of Francois Budin (UNC), Beatriz Paniagua (UNC), Lucia Cevidanes (University of Michigan), Steve Pieper (Isomics, Inc.), Jean-Baptiste Vimort (University of Michigan).
AQ3DC was developed by Baptiste Baquero (University of Michigan) in 2022 with the contribution of Maxime Gillot (University of Michigan), Lucia Cevidanes (University of Michigan), Jean-Christophe Fillion-Robin (Kitware), David Allemang (Kitware).

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

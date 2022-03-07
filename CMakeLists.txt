cmake_minimum_required(VERSION 2.8.9)

project(Q3DC)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "http://www.slicer.org/slicerWiki/index.php/Documentation/Nightly/Extensions/Q3DC")
set(EXTENSION_CATEGORY "Shape Analysis")
set(EXTENSION_CONTRIBUTORS "Lucie Macron (University of Michigan),  Jean-Baptiste Vimort (University of Michigan), James Hoctor (Kitware Inc)")
set(EXTENSION_DESCRIPTION "This extension contains one module of the same name. Using placed fiducials, it allows users to compute 2D angles: Yaw, Pitch and Roll; and decompose the 3D distance into the three different components: R-L , A-P and S-I. It is possible to compute the middle point between two fiducials and export the values.")
set(EXTENSION_ICONURL "https://raw.githubusercontent.com/DCBIA-OrthoLab/Q3DCExtension/master/Q3DC.png")
set(EXTENSION_SCREENSHOTURLS "http://www.slicer.org/slicerWiki/index.php/File:Q3DC_Interface.png")
set(EXTENSION_ENABLED 1)

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(AnglePlanes)
add_subdirectory(DependantMarkups)
add_subdirectory(PickAndPaint)
add_subdirectory(Q3DC)

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})

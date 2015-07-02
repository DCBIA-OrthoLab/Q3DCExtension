cmake_minimum_required(VERSION 2.8.9)

project(Q3DC)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "http://www.example.com/Slicer/Extensions/Q3DC")
set(EXTENSION_CATEGORY "Shape Analysis")
set(EXTENSION_CONTRIBUTORS "Lucie Macron (University of Michigan)")
set(EXTENSION_DESCRIPTION "This tool allows users to define each component of a 3D distance and to define the value of the different angle between two lines.")
set(EXTENSION_ICONURL "http://www.example.com/Slicer/Extensions/Q3DC.png")
set(EXTENSION_SCREENSHOTURLS "http://www.example.com/Slicer/Extensions/Q3DC/Screenshots/1.png")

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(Q3DC)
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_CPACK})

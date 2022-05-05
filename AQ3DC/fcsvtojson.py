import os
import glob
import csv
import json

def SaveJsonFromFcsv(file_path,out_path):
    """
    Save a .fcsv in a .json file
    Parameters
    ----------
    file_path : path of the .fcsv file 
    out_path : path of the .json file 
    """
    groupe_data = ReadFCSV(file_path)
    lm_lst = GenControlePoint(groupe_data)
    WriteJson(lm_lst,out_path)

def GenControlePoint(groupe_data):
    lm_lst = []
    false = False
    true = True
    id = 0
    for landmark,data in groupe_data.items():
        id+=1
        controle_point = {
            "id": str(id),
            "label": landmark,
            "description": "",
            "associatedNodeID": "",
            "position": [data["x"], data["y"], data["z"]],
            "orientation": [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0],
            "selected": true,
            "locked": true,
            "visibility": true,
            "positionStatus": "preview"
        }
        lm_lst.append(controle_point)

    return lm_lst

def ReadFCSV(filePath):
    """
    Read fiducial file ".fcsv" and return a liste of landmark dictionnary
    Parameters
    ----------
    filePath
     path of the .fcsv file 
    """
    Landmark_dic = {}
    with open(filePath, mode='r') as csv_file:
        csv_reader = csv.reader(csv_file)
        for row in csv_reader:
            if "#" not in row[0]:
                landmark = {}
                landmark["id"], landmark["x"], landmark["y"], landmark["z"], landmark["label"] = row[0], float(row[1]), float(row[2]), float(row[3]), row[11]
                Landmark_dic[row[11]] = landmark
    return Landmark_dic

def WriteJson(lm_lst,out_path):
    false = False
    true = True
    file = {
    "@schema": "https://raw.githubusercontent.com/slicer/slicer/master/Modules/Loadable/Markups/Resources/Schema/markups-schema-v1.0.0.json#",
    "markups": [
        {
            "type": "Fiducial",
            "coordinateSystem": "LPS",
            "locked": false,
            "labelFormat": "%N-%d",
            "controlPoints": lm_lst,
            "measurements": [],
            "display": {
                "visibility": false,
                "opacity": 1.0,
                "color": [0.4, 1.0, 0.0],
                "selectedColor": [1.0, 0.5000076295109484, 0.5000076295109484],
                "activeColor": [0.4, 1.0, 0.0],
                "propertiesLabelVisibility": false,
                "pointLabelsVisibility": true,
                "textScale": 3.0,
                "glyphType": "Sphere3D",
                "glyphScale": 1.0,
                "glyphSize": 5.0,
                "useGlyphScale": true,
                "sliceProjection": false,
                "sliceProjectionUseFiducialColor": true,
                "sliceProjectionOutlinedBehindSlicePlane": false,
                "sliceProjectionColor": [1.0, 1.0, 1.0],
                "sliceProjectionOpacity": 0.6,
                "lineThickness": 0.2,
                "lineColorFadingStart": 1.0,
                "lineColorFadingEnd": 10.0,
                "lineColorFadingSaturation": 1.0,
                "lineColorFadingHueOffset": 0.0,
                "handlesInteractive": false,
                "snapMode": "toVisibleSurface"
            }
        }
    ]
    }
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(file, f, ensure_ascii=False, indent=4)

    f.close



fcsv_dir = '/home/luciacev-admin/Desktop/AQ3DC_data'
normpath = os.path.normpath("/".join([fcsv_dir,'**','']))
lst_fscv = []
for fiducial in sorted(glob.iglob(normpath, recursive=True)):
    if os.path.isfile(fiducial) and True in [ext in fiducial for ext in [".fcsv"]]:
        lst_fscv.append(fiducial)
print(lst_fscv)
for path_fscv in lst_fscv:
    outLmPath = os.path.dirname(path_fscv) + '/' + os.path.basename(path_fscv).split('.')[0] + '.json'
    print(outLmPath)
    SaveJsonFromFcsv(path_fscv,outLmPath)
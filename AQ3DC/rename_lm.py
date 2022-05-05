import os
import json
import glob
import argparse
import pandas as pd


def ReadFolder(json_dir):
    normpath = os.path.normpath("/".join([json_dir,'**','']))
    lst_json = []
    for jsonfile in sorted(glob.iglob(normpath, recursive=True)):
        if os.path.isfile(jsonfile) and True in [ext in jsonfile for ext in [".json"]]:
            lst_json.append(jsonfile)
    return lst_json

def Rename(lst_json):
    for jsonfile in lst_json:
        print(jsonfile)
        data = json.load(open(jsonfile))
        json_file = pd.read_json(jsonfile)
        markups = json_file.loc[0,'markups']
        controlPoints = markups['controlPoints']
        number_landmarks = len(controlPoints)
        new_lst = []
        print(number_landmarks/2)
        counter = 1
        num = 7
        if "_L" in jsonfile:
            for i in range(number_landmarks):
                label = controlPoints[i]["label"]
                if i<number_landmarks/2:
                    side = 'L'
                    if label.split('-')[1] in args.oclusal:
                        name = 'O'
                    elif label.split('-')[1] in args.mesial:
                        name = 'MB'
                    elif label.split('-')[1] in args.distal:  
                        name = 'DB'  
                    elif label.split('-')[1] in args.cervicalB: 
                        name = 'CB'
                    else :  
                        name = 'CL' 
                    
                    controlPoints[i]["label"] = f'L{side}{num}{name}'
                    # print(counter,num)

                    if counter % 5 == 0:
                        num -= 1
                        counter = 1
                    else:
                        counter += 1
                    
                else :
                    side = 'R'
                    if label.split('-')[1] in args.oclusal:
                        name = 'O'
                    elif label.split('-')[1] in args.mesial:
                        name = 'MB'
                    elif label.split('-')[1] in args.distal:  
                        name = 'DB'  
                    elif label.split('-')[1] in args.cervicalB: 
                        name = 'CB'
                    else : 
                        name = 'CL' 
                    
                    controlPoints[i]["label"] = f'L{side}{num+1}{name}'
                
                    if counter % 5 == 0:
                        num += 1
                        counter = 1
                    else:
                        counter += 1

                new_lst.append(controlPoints[i])
            data['markups'][0]['controlPoints'] = new_lst
            with open(os.path.join('/home/luciacev-admin/Desktop',f"Rename_{os.path.basename(jsonfile)}"),'w') as json_file:
                json.dump(data,json_file,indent=4)

        if "_U" in jsonfile:
            for i in range(number_landmarks):
                label = controlPoints[i]["label"]
                if i<number_landmarks/2:
                    side = 'R'
                    if label.split('-')[1] in args.oclusal:
                        name = 'O'
                    elif label.split('-')[1] in args.mesial:
                        name = 'MB'
                    elif label.split('-')[1] in args.distal:  
                        name = 'DB'  
                    elif label.split('-')[1] in args.cervicalB: 
                        name = 'CB'
                    else :  
                        name = 'CL' 
                    
                    controlPoints[i]["label"] = f'U{side}{num}{name}'
                    # print(counter,num)

                    if counter % 5 == 0:
                        num -= 1
                        counter = 1
                    else:
                        counter += 1
                    
                else :
                    side = 'L'
                    if label.split('-')[1] in args.oclusal:
                        name = 'O'
                    elif label.split('-')[1] in args.mesial:
                        name = 'MB'
                    elif label.split('-')[1] in args.distal:  
                        name = 'DB'  
                    elif label.split('-')[1] in args.cervicalB: 
                        name = 'CB'
                    else : 
                        name = 'CL' 
                    
                    controlPoints[i]["label"] = f'U{side}{num+1}{name}'
                
                    if counter % 5 == 0:
                        num += 1
                        counter = 1
                    else:
                        counter += 1

                new_lst.append(controlPoints[i])
            data['markups'][0]['controlPoints'] = new_lst
            with open(os.path.join('/home/luciacev-admin/Desktop',f"Rename_{os.path.basename(jsonfile)}"),'w') as json_file:
                json.dump(data,json_file,indent=4)

        

def main(args):
    lst_json = ReadFolder(args.jsondir)
    print(lst_json)
    Rename(lst_json)
    # print(lst_json)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='separAte all the teeth from a vtk file', formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    input_param = parser.add_argument_group('input files')
    input_param.add_argument('--jsondir', type=str, help='Directory with all the project', default='/home/luciacev-admin/Desktop/AQ3DC_data')
    input_param.add_argument('--oclusal', type=list, help='Directory with all the project', default=['3','8','13','18','23','28','33','38','43','48','53','58','63','68'])
    input_param.add_argument('--mesial', type=list, help='Directory with all the project', default=['5','10','15','20','25','30','35','39','44','49','54','59','64','69'])
    input_param.add_argument('--distal', type=list, help='Directory with all the project', default=['4','9','14','19','24','29','34','40','45','50','55','60','65','70'])
    input_param.add_argument('--cervicalB', type=list, help='Directory with all the project', default=['2','7','12','17','22','27','32','37','42','47','52','57','62','67'])
    input_param.add_argument('--cervicalL', type=list, help='Directory with all the project', default=['1','6','11','16','21','26','31','36','41','46','51','56','61','66'])
    

    args = parser.parse_args()
    main(args)


#    else :
#             data_u = json.load(open(jsonfile)
#             json_file = pd.read_json(jsonfile))
#             markups = json_file.loc[0,'markups']
#             controlPoints = markups['controlPoints']
#             number_landmarks = len(controlPoints)
#             new_lst = []
            
#             counter = 0
#             for i in range(number_landmarks):
#                 if i<len(number_landmarks)/2:
#                     side = 'U'
#                     num = 7
#                     if label.split('-')[1] in args.oclusal:
#                         name = 'O'
#                     elif label.split('-')[1] in args.mesial:
#                         name = 'MB'
#                     elif label.split('-')[1] in args.distal:  
#                         name = 'DB'  
#                     elif label.split('-')[1] in args.cervicalB: 
#                         name = 'CB'
#                     else :  
#                         name = 'CL' 
                    
#                     controlPoints[i]["label"] = f'L{side}{num}{name}'
                    
#                     if counter % 5 == 0:
#                         num -= 1
#                         counter = 0
#                     else:
#                         counter += 1

                    
#                 else :
#                     side = 'R'
#                     num = 1
#                     if label.split('-')[1] in Oclusal_landmarks:
#                         name = 'O'
#                     elif label.split('-')[1] in MisialBucal_landmarks:
#                         name = 'MB'
#                     elif label.split('-')[1] in DistalBucal_landmarks:  
#                         name = 'DB'  
#                     elif label.split('-')[1] in CervicalBucal_landmarks: 
#                         name = 'CB'
#                     else : 
#                         name = 'CL' 
                    
#                     controlPoints[i]["label"] = f'L{side}{num}{name}'
#                     if counter % 5 == 0:
#                         num += 1
#                         counter = 0
#                     else:
#                         counter += 1



#                 new_lst.append(controlPoints[i])
#             print(new_lst)
#             data_u['markups'][0]['controlPoints'] = new_lst
#             print(os.path.join(outdir,f"Rename_{os.path.basename(jsonfile)}")
#             with open(os.path.join(outdir,f"Rename_{os.path.basename(jsonfile)}"),'w') as json_file:
#                 json.dump(data_u,json_file,indent=4)
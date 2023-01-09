
from dataclasses import dataclass
import pandas as pd
import itertools

@dataclass(init=False)
class Group_landmark:
    


    def __init__(self,path_listlandmarks) -> None:
        self.group_landmark  = dict()
        reader = pd.read_excel(path_listlandmarks)
        header_before = 'b suisv'

        for header in reader.keys() :

            if header_before in header:

                header2=header.split('-')[1]
                Type = self.group_landmark[header_before]
                tmplist= []
                for landmark in reader[header].tolist():
                    if isinstance(landmark,str):
                        tmplist.append(landmark)
                self.group_landmark[header_before] = Type.add({header2:tmplist})


            else :
                header_before = header
                tmplist = []
                for landmark in reader[header].tolist():
                    if isinstance(landmark,str):
                        tmplist.append(landmark)

                self.group_landmark[header] = Type1(tmplist)

        
    def __repr__(self):
        return f'{self.group_landmark}'


    def __contains__(self,landmark):
        out = False 
        for landmarks in self.group_landmark.values():
            if landmark in landmarks:
                out = True
                break
        
        return out




    def exits(self,list_landmark):
        dic_out = {key : False for key in self.tolist() }

        for landmark in list_landmark:
            if self.__contains__(landmark):
                dic_out.update(self.find(landmark))
                # dic_out[landmark] = True


        return dic_out


    def find(self,landmark):
        out = {landmark: False}
        for type in self.group_landmark.values():
            if landmark in type:
                out = type.find(landmark)
                break
        return out






    def tolist(self):
        out_list = []
        for values in self.group_landmark.values():
            out_list += values.tolist()

        return out_list



    def __setitem__(self,key,value):
        if isinstance(value,list):
            self.group_landmark[key]= Type1(value)
        elif isinstance(value,str):
            self.group_landmark[key].set(value)


    def __getitem__(self,key):
        return self.group_landmark[key]



    def items(self):
        return self.group_landmark.items()

    
    def fusion(self,list_landmark):
        for landmarks in self.group_landmark.values():
            if isinstance(landmarks,Type2):
                landmarks.fusion(list_landmark)

        return list_landmark




@dataclass(repr=True)
class Type1:
    suffix : list


    def add(self,dic):
        return Type2(suffix = self.suffix, prefix = dic)

    def __contains__(self,landmark):
        return landmark.upper() in [lm.upper() for lm in self.suffix]

    def find(self,landmark):
        out = False
        if self.__contains__(landmark): 
            out = True

        return {landmark:out}

    def __iter__(self):
        self.iter = -1
        return self

    def __next__(self):
        if self.iter +1 >= len(self.suffix):
            raise StopIteration
        self.iter +=1
        return self.suffix[self.iter]

    def set(self,value):
        self.suffix.append(value)


    def tolist(self):
        return self.suffix



@dataclass(repr=True)
class Type2(Type1):
    prefix : dict


    def __contains__(self,landmark) :
        
        out = False
        pre , suf = self.decomp(landmark)
        if not None in (pre,suf) :
            out = True
        return out

    def decomp(self,landmark : str):
        pre = None
        suf = None
        for prefix in list(itertools.chain.from_iterable(self.prefix.values())):
            if prefix.upper()  == landmark[:len(prefix)].upper():
                for suffix in self.suffix :
                    if suffix.upper() == landmark[len(prefix):].upper():
                        pre = prefix.upper()
                        suf = suffix.upper()
                        break
        return pre, suf

    def find(self,landmark):
        pre, suf  = self.decomp(landmark)
        out = {landmark : False}
        if not None in (pre , suf):
            out = {pre:True,suf:True}

        return out

    def add(self,dic):
        copy  = self.prefix
        copy.update(dic)
        return Type2(prefix = copy,suffix=self.suffix)

    def get(self):
        return self.prefix.copy(), self.suffix.copy()

    def tolist(self):

        return self.suffix + list(itertools.chain.from_iterable(self.prefix.values()))


    def fusion(self,list_landmark : list):
        dic = {'prefix':list(),'suffix':list()}
        for landmark in list_landmark:
            for suf in self.suffix:
                if landmark == suf:
                    dic['suffix'].append(landmark)
                    continue

            for pre in list(itertools.chain.from_iterable(self.prefix.values())):
                if landmark == pre :
                    dic['prefix'].append(landmark)

        for suf in dic['suffix']:
            list_landmark.remove(suf)
        for pre in dic['prefix'] :
            list_landmark.remove(pre)
            for suf in dic['suffix'] :
                
                list_landmark.append(pre+suf)

        return list_landmark

        


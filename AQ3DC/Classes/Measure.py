from Classes.Point import Point
from Classes.Line import Line
import numpy as np


upper_right_back = ["UR8", "UR7", "UR6", "UR5", "UR4", "UR3"]
upper_right_front = ["UR1", "UR2"]
upper_left_back = ["UL8", "UL7", "UL6", "UL5", "UL4", "UL3"]
upper_left_front = ["UL1", "UL2"]
lower_right_back = ["LR8", "LR7", "LR6", "LR5", "LR4", "LR3"]
lower_right_front = ["LR1", "LR2"]
lower_left_back = ["LL8", "LL7", "LL6", "LL5", "LL4", "LL3"]
lower_left_front = ["LL1", "LL2"]


class Measure:
    def __init__(self, time: str, measure: str):
        self.time = time

        self.measure = measure
        self.checkbox = None
        self.lr_sign_meaning = ""
        self.ap_sign_meaning = ""
        self.si_sign_meaning = ""
        self.lr, self.ap, self.si, self.norm = 0, 0, 0, 0

    def __str__(self):
        strs = self.measure
        if self.time:
            strs += " " + self.time
        if self.checkbox:
            if self.checkbox.checkState():
                strs += " True "
            else:
                strs += " False "
        return strs

    def __setitem__(self, key, value):
        if key == "checkbox":
            self.checkbox = value

    def __getitem__(self, key):
        if key == "checkbox" or key == "check box":
            return self.checkbox
        elif key == "Type of measurement":
            return self.measure
        elif key == "Type of measurement + time":
            if self.time:
                return self.measure + " " + self.time
            else:
                return self.measure
        return "x"

    def __eq__(self, __o: object) -> bool:
        out = False
        if self["Type of measurement + time"] == __o["Type of measurement + time"]:
            out = True
        return out

    def isUpperLower(self, landmark):

        List = [
            "LL7",
            "LL6",
            "LL5",
            "LL4",
            "LL3",
            "LL2",
            "LL1",
            "LR1",
            "LR2",
            "LR3",
            "LR4",
            "LR5",
            "LR6",
            "LR7",
            "UL7",
            "UL6",
            "UL5",
            "UL4",
            "UL3",
            "UL2",
            "UL1",
            "UR1",
            "UR2",
            "UR3",
            "UR4",
            "UR5",
            "UR6",
            "UR7",
        ]
        loop = 1
        if "mid" in landmark.upper():
            loop = 2
        out = True
        for i in range(loop):
            if not True in [l in landmark for l in List]:
                out = False
        return out


class Distance(Measure):
    def __init__(
        self, Point1: Point, Point2Line, measure: str, time: str = None
    ) -> None:
        super().__init__(time, measure)

        self.point1 = Point1
        self.point2line = Point2Line

    def __str__(self) -> str:
        strs = f"{Measure.__str__(self)} Point 1 : {self.point1} Point 2 /Line :{self.point2line}"
        return strs

    def __repr__(self) -> str:
        return self.__str__()

    def __setitem__(self, key, value):
        if key == "position":
            self.point1["position"] = value
            self.point2line["position"] = value

        Measure.__setitem__(self, key, value)

    def __getitem__(self, key):
        if key == "point 1" or key == 1:
            return self.point1
        elif key == "point 2" or key == 2:
            return self.point2line
        elif key == "Landmarks":
            return str(self.point1) + " - " + str(self.point2line)
        elif key == "R-L Component":
            return str(abs(self.lr))
        elif key == "R-L Meaning":
            return self.lr_sign_meaning
        elif key == "A-P Component":
            return str(abs(self.ap))
        elif key == "A-P Meaning":
            return self.ap_sign_meaning
        elif key == "S-I Component":
            return str(abs(self.si))
        elif key == "S-I Meaning":
            return self.si_sign_meaning
        elif key == "3D Distance":
            return self.norm
        elif key == "group":
            return "Distance"
        return Measure.__getitem__(self, key)


    def __eq__(self, __o: object) -> bool:
        out = False
        if super().__eq__(__o):
            if self.point1 == __o[1] and self.point2line == __o[2]:

                out = True
        return out
    
    def IterBasicInformation(self):
        yield self.__getitem__('Type of measurement + time')
        yield self.__getitem__('point 1')
        yield self.__getitem__('point 2')

    def computation(self):
        if "Distance between 2 points" in self["Type of measurement"]:
            self.lr, self.ap, self.si, self.norm = self.__computeDistance(
                np.array(self.point1["position"]), np.array(self.point2line["position"])
            )
        elif "Distance point line" in self["Type of measurement"]:
            self.lr, self.ap, self.si, self.norm = self.__computeLinePoint(
                np.array(self.point2line[1]["position"]),
                np.array(self.point2line[2]["position"]),
                np.array(self.point1["position"]),
            )

    def isUtilMeasure(self):
        out = True

        if self.norm == 0:
            out = False

        return out

    def __computeDistance(self, point1_coord, point2_coord):
        delta = point2_coord - point1_coord
        norm = np.linalg.norm(delta)

        return (
            round(-delta[0], 3),
            round(-delta[1], 3),
            round(delta[2], 3),
            round(norm, 3),
        )

    def __reject(self, vec, axis):
        vec = np.asarray(vec)
        axis = np.asarray(axis)

        return vec - axis * (np.dot(vec, axis) / np.dot(axis, axis))

    def __computeLinePoint(self, line1, line2, point):
        if np.allclose(line1, line2, atol=1e-5):
            delta = point - line1
        else:
            delta = self.__reject(point - line2, line1 - line2,)
        norm = np.linalg.norm(delta)
        return (
            round(-delta[0], 3),
            round(-delta[1], 3),
            round(delta[2], 3),
            round(norm, 3),
        )

    def SignManager(self):
        if self.measure == "Distance between 2 points":
            if self.isUpperLower(self.point1["name"]) and self.isUpperLower(
                self.point2line["name"]
            ):
                self.__SignMeaningDentalDst()
            else:
                self.__SignMeaningDist()

        else:
            self.__SignMeaningDist()

    def __SignMeaningDist(self):
        self.lr_sign_meaning = "L"
        self.ap_sign_meaning = "P"
        self.si_sign_meaning = "I"
        if self.lr > 0:
            self.lr_sign_meaning = "R"  # Right

        if self.ap > 0:
            self.ap_sign_meaning = "A"  # Anterior

        if self.si > 0:
            self.si_sign_meaning = "S"  # Superior

    def __SignMeaningDentalDst(self):
        lst_measurement = [self.point1["name"], self.point2line["name"]]
        if check(lst_measurement, upper_right_back):
            self.lr_sign_meaning = "L"
            self.ap_sign_meaning = "D"
            self.si_sign_meaning = "E"
            if self.lr > 0:
                self.lr_sign_meaning = "B"

            if self.ap > 0:
                self.ap_sign_meaning = "M"

            if self.si > 0:
                self.si_sign_meaning = "I"

        elif check(lst_measurement, upper_right_front):
            self.lr_sign_meaning = "M"
            self.ap_sign_meaning = "L"
            self.si_sign_meaning = "E"
            if self.lr > 0:
                self.lr_sign_meaning = "D"

            if self.ap > 0:
                self.ap_sign_meaning = "B"

            if self.si > 0:
                self.si_sign_meaning = "I"

        elif check(lst_measurement, upper_left_back):
            self.rl_sign_meaning = "B"
            self.ap_sign_meaning = "D"
            self.si_sign_meaning = "E"
            if self.lr > 0:
                self.rl_sign_meaning = "L"

            if self.ap > 0:
                self.ap_sign_meaning = "M"

            if self.si > 0:
                self.si_sign_meaning = "I"

        elif check(lst_measurement, upper_left_front):
            self.si_sign_meaning = "E"
            self.ap_sign_meaning = "L"
            self.rl_sign_meaning = "D"
            if self.lr > 0:
                self.rl_sign_meaning = "M"

            if self.ap > 0:
                self.ap_sign_meaning = "B"

            if self.si > 0:
                self.si_sign_meaning = "I"

        elif check(lst_measurement, lower_right_back):
            self.rl_sign_meaning = "L"
            self.ap_sign_meaning = "D"
            self.si_sign_meaning = "I"
            if self.lr > 0:
                self.rl_sign_meaning = "B"

            if self.ap > 0:
                self.ap_sign_meaning = "M"

            if self.si > 0:
                self.si_sign_meaning = "E"

        elif check(lst_measurement, lower_right_front):
            self.rl_sign_meaning = "M"
            self.ap_sign_meaning = "L"
            self.si_sign_meaning = "I"
            if self.lr > 0:
                self.rl_sign_meaning = "D"

            if self.ap > 0:
                self.ap_sign_meaning = "B"

            if self.si > 0:
                self.si_sign_meaning = "E"

        elif check(lst_measurement, lower_left_back):
            self.rl_sign_meaning = "B"
            self.ap_sign_meaning = "D"
            self.si_sign_meaning = "I"
            if self.lr > 0:
                self.rl_sign_meaning = "L"

            if self.ap > 0:
                self.ap_sign_meaning = "M"

            if self.si > 0:
                self.si_sign_meaning = "E"

        elif check(lst_measurement, lower_left_front):
            self.rl_sign_meaning = "D"
            self.ap_sign_meaning = "L"
            self.si_sign_meaning = "I"
            if self.lr > 0:
                self.rl_sign_meaning = "M"

            if self.ap > 0:
                self.ap_sign_meaning = "B"

            if self.si > 0:
                self.si_sign_meaning = "E"


class Angle(Measure):
    def __init__(self, Line1: Line, Line2: Line, measure: str, time: str = None):
        super().__init__(time, measure)
        self.line1 = Line1
        self.line2 = Line2
        self.complement_checkbox = None

    def __str__(self) -> str:
        return f"{Measure.__str__(self)} Line 1 : {self.line1} Line 2 : {self.line2}"

    def __repr__(self) -> str:
        return self.__str__()

    def __getitem__(self, key):
        if key == "line 1" or key == 1:
            return self.line1
        elif key == "line 2" or key == 2:
            return self.line2
        elif key == "Landmarks":
            return str(self.line1) + " / " + str(self.line2)
        elif key == "Yaw Component":
            return str(abs(self.lr))
        elif key == "Yaw Meaning":
            return self.lr_sign_meaning
        elif key == "Pitch Component":
            return str(abs(self.ap))
        elif key == "Pitch Meaning":
            return self.ap_sign_meaning
        elif key == "Roll Component":
            return str(abs(self.si))
        elif key == "Roll Meaning":
            return self.si_sign_meaning
        elif key == "complement":
            return self.complement_checkbox
        elif key == "group":
            return "Angle"
        return Measure.__getitem__(self, key)

    def __setitem__(self, key, value):
        if key == "position":
            self.line1["position"] = value
            self.line2["position"] = value
        elif key == "complement":
            self.complement_checkbox = value

        return super().__setitem__(key, value)

    def __eq__(self, __o: object) -> bool:
        out = False
        if Measure.__eq__(self, __o):
            if (
                self.line1 == __o[1]
                and self.line2 == __o[2]
                and (self.complement_checkbox is None or  self.complement_checkbox.isChecked())
            ):
                out = True
        return out
    
    def IterBasicInformation(self):
        yield self.__getitem__('Type of measurement + time')
        yield self.__getitem__('line 1')
        yield self.__getitem__('line 2')

    def computation(self):
        self.lr, self.ap, self.si = self.__computeAngles(
            np.array(self.line1[1]["position"]),
            np.array(self.line1[2]["position"]),
            np.array(self.line2[1]["position"]),
            np.array(self.line2[2]["position"]),
        )

    def isUtilMeasure(self):
        out = True

        if self.lr == 0 and self.ap == 0 and self.si == 0:
            out = False

        return out

    def SignManager(self):
        if (
            self.isUpperLower(self.line1[1]["name"])
            and self.isUpperLower(self.line1[2]["name"])
            and self.isUpperLower(self.line2[1]["name"])
            and self.isUpperLower(self.line2[2]["name"])
        ):
            self.__SignMeaningDentalAngle()

    def __computeAngle(self, line1, line2, axis):
        mask = [True] * 3
        mask[axis] = False
        line1 = line1[mask]
        line2 = line2[mask]

        norm1 = np.linalg.norm(line1)
        norm2 = np.linalg.norm(line2)

        matrix = np.array([line1, line2])
        det = np.linalg.det(matrix)
        if norm1 == 0 or norm2 == 0:
            raise ZeroDivisionError(line1, line2)
        radians = np.arcsin(det / norm1 / norm2)
        return np.degrees(radians)

    def __computeAngles(self, point1, point2, point3, point4):
        line1 = point2 - point1
        line2 = point4 - point3
        axes = [
            2,  # axis=S; axial; for yaw
            0,  # axis=R; saggital; for pitch
            1,  # axis=A; coronal; for roll
        ]
        result = []
        for axis in axes:
            value = self.__computeAngle(line1, line2, axis)
            result.append(round(value, 3))

        if self.complement_checkbox is not None and self.complement_checkbox.isChecked():
            tmp_result = []
            for resu in result:
                new_resu = round(180 - np.absolute(resu), 3)
                tmp_result.append(new_resu)

            result = tmp_result

        return result[0], -result[1], -result[2]

    def __SignMeaningDentalAngle(self):
        lst_measurement = [
            self.line1[1]["name"],
            self.line1[2]["name"],
            self.line2[1]["name"],
            self.line2[2]["name"],
        ]
        # print("function angle")
        if check(lst_measurement, upper_right_back):
            self.lr_sign_meaning = "D"
            self.ap_sign_meaning = "L"
            self.si_sign_meaning = "DR"
            if self.lr > 0:
                self.lr_sign_meaning = "M"

            if self.ap > 0:
                self.ap_sign_meaning = "B"

            if self.si > 0:
                self.si_sign_meaning = "MR"

        elif check(lst_measurement, upper_right_front):
            self.lr_sign_meaning = "L"
            self.ap_sign_meaning = "M"
            self.si_sign_meaning = "DR"
            if self.lr > 0:
                self.lr_sign_meaning = "B"

            if self.ap > 0:
                self.ap_sign_meaning = "D"

            if self.si > 0:
                self.si_sign_meaning = "MR"

        elif check(lst_measurement, upper_left_back):
            self.lr_sign_meaning = "D"
            self.ap_sign_meaning = "B"
            self.si_sign_meaning = "MR"
            if self.lr > 0:
                self.lr_sign_meaning = "M"

            if self.ap > 0:
                self.ap_sign_meaning = "L"

            if self.si > 0:
                self.si_sign_meaning = "DR"

        elif check(lst_measurement, upper_left_front):
            self.lr_sign_meaning = "L"
            self.ap_sign_meaning = "D"
            self.si_sign_meaning = "MR"
            if self.lr > 0:
                self.lr_sign_meaning = "B"

            if self.ap > 0:
                self.ap_sign_meaning = "M"

            if self.si > 0:
                self.si_sign_meaning = "DR"

        elif check(lst_measurement, lower_right_back):
            self.lr_sign_meaning = "M"
            self.ap_sign_meaning = "B"
            self.si_sign_meaning = "DR"
            if self.lr > 0:
                self.lr_sign_meaning = "D"

            if self.ap > 0:
                self.ap_sign_meaning = "L"

            if self.si > 0:
                self.si_sign_meaning = "MR"

        elif check(lst_measurement, lower_right_front):
            self.lr_sign_meaning = "B"
            self.ap_sign_meaning = "D"
            self.si_sign_meaning = "DR"
            if self.lr > 0:
                self.lr_sign_meaning = "L"

            if self.ap > 0:
                self.ap_sign_meaning = "M"

            if self.si > 0:
                self.si_sign_meaning = "MR"

        elif check(lst_measurement, lower_left_back):
            self.lr_sign_meaning = "M"
            self.ap_sign_meaning = "L"
            self.si_sign_meaning = "MR"
            if self.lr > 0:
                self.lr_sign_meaning = "D"

            if self.ap > 0:
                self.ap_sign_meaning = "B"

            if self.si > 0:
                self.si_sign_meaning = "DR"

        elif check(lst_measurement, lower_left_front):
            self.lr_sign_meaning = "B"
            self.ap_sign_meaning = "M"
            self.si_sign_meaning = "MR"
            if self.lr > 0:
                self.lr_sign_meaning = "L"

            if self.ap > 0:
                self.ap_sign_meaning = "D"

            if self.si > 0:
                self.si_sign_meaning = "DR"


class Diff2Measure(Measure):
    def __init__(self, measure1, measure2) -> None:
        super().__init__(time="T1 T2", measure=measure1["Type of measurement"])
        self.T1PL1 = measure1[1]
        self.T1PL2 = measure1[2]
        self.T2PL1 = measure2[1]
        self.T2PL2 = measure2[2]
        self.measure1 = measure1
        self.measure2 = measure2

    def __str__(self):

        out = f"{Measure.__str__(self)} {self.T1PL1}/{self.T2PL1} {self.T1PL2}/{self.T2PL2}"
        return out

    def __repr__(self) -> str:
        return self.__str__()


    def __getitem__(self, key):
        if key == "measure 1" or key == 1:
            return self.measure1
        elif key == "measure 2" or key == 2:
            return self.measure2
        elif key == "Landmarks":
            return self.measure1["Landmarks"] + " && " + self.measure2["Landmarks"]
        elif isinstance(self.measure1, Distance):
            if key == "R-L Component":
                return str(abs(self.lr))
            elif key == "A-P Component":
                return str(abs(self.ap))
            elif key == "S-I Component":
                return str(abs(self.si))
            elif key == "3D Distance":
                return str(
                    round(np.linalg.norm(np.array([self.lr, self.ap, self.si])), 3)
                )
            elif key == "group":
                return "Distance"
        elif isinstance(self.measure1, Angle):
            if key == "Yaw Component":
                return str(abs(self.lr))
            elif key == "Pitch Component":
                return str(abs(self.ap))
            elif key == "Roll Component":
                return str(abs(self.si))
            elif key == "group":
                return "Angle"
        return super().__getitem__(key)

    def __setitem__(self, key, value):
        if key == "position":
            self.measure1["position"] = value
            self.measure2["position"] = value
        elif "complement" == key:
            self.measure1["complement"] = value
            self.measure2["complement"] = value

        return super().__setitem__(key, value)

    def __eq__(self, __o: object) -> bool:
        out = False
        if Measure.__eq__(self, __o):
            if self.measure1 == __o[1] and self.measure2 == __o[2]:
                out = True
        return out
    
    def IterBasicInformation(self):
        yield self.__getitem__('Type of measurement + time')
        yield f'{self.T1PL1}/{self.T2PL1}'
        yield f'{self.T1PL2}/{self.T2PL2}'

    def computation(self):
        self.measure1.computation()
        self.measure2.computation()
        self.lr = self.measure2.lr - self.measure1.lr
        self.ap = self.measure2.ap - self.measure1.ap
        self.si = self.measure2.si - self.measure1.si
        self.lr = round(self.lr, 3)
        self.ap = round(self.ap, 3)
        self.si = round(self.si, 3)

    def isUtilMeasure(self):
        out = True
        if self.lr == 0 and self.ap == 0 and self.si == 0:
            out == False

        return out

    def SignManager(self):
        # it is normal
        # we dont need to compute the meaning of measurement
        pass


def check(list_landmark, tocheck):
    nb_correct = 0
    nb_midpoint = 0
    for landmark in list_landmark:
        if "mid".upper() in landmark.upper():
            nb_midpoint += 1

        for check in tocheck:

            if check in landmark:
                nb_correct += 1

    out = False
    if nb_correct == len(list_landmark) + nb_midpoint:
        out = True

    return out

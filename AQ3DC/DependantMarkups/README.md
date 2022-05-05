# Dependant Markups

Use a `DependantMarkupsLogic` to manage and compute measurements between control points of a `vtkMRMLMarkupsNode`.

```python
import slicer, vtk
from  DependantMarkups import DependantMarkupsLogic

logic = DependantMarkupsLogic()

node = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode')
model = slicer.mrmlScene.GetNodeByID(...)  # a vtkMRMLModelNode

logic.connect(node, model)
```

`logic.connect` adds observers so that when points are added, modified, or removed, the `DependantMarkups` metadata is updated accordingly.

## Options

### Midpoint

Add a point ID at the midpoint between two other points. When either of the points is updated, the midpoint will be also.

```python
index = node.AddControlPoint(vtk.vtkVector3d())
ID = node.GetNthControlPointID(index)

ID1 = ...  # a ControlPoint ID
ID2 = ...

logic.setMidPoint(node, ID, ID1, ID2)
```

### Projection

Lock a point to a model. When the point is updated, it will remain locked to the model.

```python
ID = ...  # a ControlPoint ID

logic.setProjected(node, ID, True)  # or False to unlock
```

Make new points project to a model

```python
logic.default_projected = True  # or False to unlock
```

Change the model used for projection

```python
logic.connect(node, other_model)
```

Lock a midpoint to a model.

```python
logic.setProjected(node, ID, True)  # or False to unlock
logic.setProjected(node, ID, ID1, ID2)
```

## Computations

### Point-to-Point Distance

```python
point1 = logic.getNthControlPointPositionByID(node, ...)
point2 = logic.getNthControlPointPositionByID(node, ...)

result = logic.computeDistance(point1, point2)

print(result.delta)  # component-wise distance
print(result.norm)  # 3D euclidean distance
```

### Point-to-Line Distance

```python
linePoint1 = logic.getNthControlPointPositionByID(node, ...)
linePoint2 = logic.getNthControlPointPositionByID(node, ...)
point = logic.getNthControlPointPositionByID(node, ...)

result = logic.computeLinePoint(linePoint1, linePoint2, point)

print(result.delta)  # component-wise distance
print(result.norm)  # 3D euclidean distance
```

### Line-to-Line Angle

```python
line1Point1 = logic.getNthControlPointPositionByID(node, ...)
line1Point2 = logic.getNthControlPointPositionByID(node, ...)
line2Point1 = logic.getNthControlPointPositionByID(node, ...)
line2Point2 = logic.getNthControlPointPositionByID(node, ...)

line1Vector = line1Point2 - line1Point1
line2Vector = line2Point2 - line2Point1

result = logic.computeAngles(line1Vector, line2Vector)

# values in degrees
print(result.byaxis)  # axis-wise angles
print(result.absolute)  # absolute 3D angle
```

Compute line angle by arbitrary axis

```python
axis = (1, 2, 3)  # arbitrary vector defining a plane
angle = logic.computeAngle(line1Vector, line2Vector, axis)

print(angle)  # angle measured in the plane defined by axis. float value in degrees.
```

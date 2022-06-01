Desired API:

```python
import slicer, vtk
from MarkupConstraints import MarkupConstraintsLogic

from typing import Union, Tuple

node = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode')
model = slicer.mrmlScene.GetNodeByID(...)  # a vtkMRMLModelNode

logic = MarkupConstraintsLogic

cons = logic._constraints(node, model)

# cons[ID] = Constraints.MidPoint(ID1, ID2, project=True)
# cons[ID] = Constraints.Free(project=True)

cons.set(ID, MidPoint(ID1, ID2), project=True)
cons.free(ID)

ControlPoint = Union[str, Tuple[str, 'node']]


def MidPoint(
    ID1: ControlPoint,
    ID2: ControlPoint,
): ...


def LockTo(
    ID: ControlPoint,
): ...
```

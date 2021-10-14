# SlicerCMF Landmarks Attributes 

Q3DC and related SlicerCMF extensions use [MRML node attributes][attributes] to encode 
constraints on landmark positions like projecting a point to the surface of a model, or
keeping a point at the midpoint of two others.

[attributes]: https://slicer.readthedocs.io/en/latest/developer_guide/mrml_overview.html#mrml-node-attributes

## `connectedModelID`

Stores the ID of the model to which landmarks are projected.

## `hardenModelID`

Since the connected model may be transformed, the _hardened_ model has these transforms 
applied such that all its coordinates are in world space, suitable for computing landmark
projections. 

## `landmarkDescription`

A JSON string storing landmark constraints and related metadata. See the 
[`landmarkDescription` JSON Schema][schema] or open in the 
[Atlassian JSON Schema Viewer][viewer] for details. The JSON contains the following:

- Landmark legend labels (overriding `vtkMRMLMarkupsNode::MarkupLabelFormat`)
- Projection to model surface constraints
- Midpoint constraints
- Constraint dependencies (i.e. if a landmark is modified, which constrained landmarks should also update)

[schema]: ./landmarkDescription.schema.json
[viewer]: https://json-schema.app/view/%23?url=https%3A%2F%2Fraw.githubusercontent.com%2FDCBIA-OrthoLab%2FQ3DCExtension%2Fmaster%2Fdocs%2FlandmarkDescription.schema.json

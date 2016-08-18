# character_extraction

## `ExtractCharacterLocations.js` and `main.js`

Dependencies: [Jimp](https://github.com/oliver-moran/jimp)

Installation: `npm install --save jimp`

There are two methods of the API:

1. `extractCharacterLocations.getAll()`
2. `extractCharacterLocations.getNearCoord()`

Currently both are partially complete, and only `extractCharacterLocations.getNearCoord` is tested.

Details to be filled in soon.

To run on command line in debug mode:
`node main.js imageFileOfChoice xCoordinate yCoordinate`


## `character_extraction_prototype.py`

This is used to prototype

Dependencies: [Pillow/PIL](https://python-pillow.github.io/)

To run on command line in debug mode:
`char_extraction.py image.png x_coordinate y_coordinate`

Ex:
`char_extraction.py test.png 734 166`

To run on a full image:
`char_extraction.py image.png`

# character_extraction

## `extractCharacterLocations.js` and `main.js`

Dependencies: [Jimp](https://github.com/oliver-moran/jimp)

Installation: `npm install --save jimp`

There are two ways of extracting characters:

1. `extractCharacterLocations.getAll()`
2. `extractCharacterLocations.getNearCoord()`


The two methods are wrapped by `main.js`.

To run on command line:

`node main.js imageFileOfChoice`

or 

`node main.js imageFileOfChoice xCoordinate yCoordinate`


The current setup will save images of:

1. Full image with locations of bubbles marked
2. Full image with locations of sub-bubbles marked
3. Full image with locations of character locations marked

## `character_extraction_prototype.py`

This is used to prototype

Dependencies: [Pillow/PIL](https://python-pillow.github.io/)

To run on command line in debug mode:
`char_extraction.py image.png x_coordinate y_coordinate`

Ex:
`char_extraction.py test.png 734 166`

To run on a full image:
`char_extraction.py image.png`

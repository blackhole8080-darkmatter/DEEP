import { readFileSync } from 'fs';
import * as topojson from 'topojson-client';
const worldData = JSON.parse(readFileSync('./src/components/console/world.json'));
const land = topojson.feature(worldData, worldData.objects.countries);
console.log(Array.isArray(land.features) ? 'FeatureCollection with ' + land.features.length + ' features' : 'Not a FeatureCollection');
console.log(land.type);

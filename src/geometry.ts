import type { Coordinate } from "./types.js";

const EARTH_RADIUS_KM = 6_371.0088;
const DEGREES_TO_RADIANS = Math.PI / 180;

export type PolylineProjection = Readonly<{
  distanceKm: number;
  progress: number;
  segmentIndex: number;
  segmentFraction: number;
}>;

export function haversineDistanceKm(left: Coordinate, right: Coordinate): number {
  const leftLatitude = left.latitude * DEGREES_TO_RADIANS;
  const rightLatitude = right.latitude * DEGREES_TO_RADIANS;
  const latitudeDelta = (right.latitude - left.latitude) * DEGREES_TO_RADIANS;
  const longitudeDelta = (right.longitude - left.longitude) * DEGREES_TO_RADIANS;
  const sinLatitude = Math.sin(latitudeDelta / 2);
  const sinLongitude = Math.sin(longitudeDelta / 2);
  const a =
    sinLatitude * sinLatitude +
    Math.cos(leftLatitude) * Math.cos(rightLatitude) * sinLongitude * sinLongitude;
  return 2 * EARTH_RADIUS_KM * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function toLocalKilometers(
  coordinate: Coordinate,
  latitudeReferenceRadians: number,
): Readonly<{ x: number; y: number }> {
  return {
    x:
      EARTH_RADIUS_KM *
      coordinate.longitude *
      DEGREES_TO_RADIANS *
      Math.cos(latitudeReferenceRadians),
    y: EARTH_RADIUS_KM * coordinate.latitude * DEGREES_TO_RADIANS,
  };
}

export function projectPointOntoPolyline(
  point: Coordinate,
  geometry: readonly Coordinate[],
): PolylineProjection {
  if (geometry.length < 2) {
    throw new Error("Polyline projection requires at least two geometry points.");
  }

  const referenceLatitude = point.latitude * DEGREES_TO_RADIANS;
  const localPoint = toLocalKilometers(point, referenceLatitude);
  const segmentLengths = geometry
    .slice(0, -1)
    .map((coordinate, index) => haversineDistanceKm(coordinate, geometry[index + 1] as Coordinate));
  const totalLength = segmentLengths.reduce((sum, length) => sum + length, 0);

  let bestDistanceSquared = Number.POSITIVE_INFINITY;
  let bestSegmentIndex = 0;
  let bestSegmentFraction = 0;
  let completedLength = 0;
  let bestCompletedLength = 0;

  for (let index = 0; index < geometry.length - 1; index += 1) {
    const start = toLocalKilometers(geometry[index] as Coordinate, referenceLatitude);
    const end = toLocalKilometers(geometry[index + 1] as Coordinate, referenceLatitude);
    const deltaX = end.x - start.x;
    const deltaY = end.y - start.y;
    const squaredLength = deltaX * deltaX + deltaY * deltaY;
    const fraction =
      squaredLength === 0
        ? 0
        : Math.max(
            0,
            Math.min(
              1,
              ((localPoint.x - start.x) * deltaX + (localPoint.y - start.y) * deltaY) /
                squaredLength,
            ),
          );
    const projectedX = start.x + fraction * deltaX;
    const projectedY = start.y + fraction * deltaY;
    const distanceX = localPoint.x - projectedX;
    const distanceY = localPoint.y - projectedY;
    const distanceSquared = distanceX * distanceX + distanceY * distanceY;

    if (distanceSquared < bestDistanceSquared) {
      bestDistanceSquared = distanceSquared;
      bestSegmentIndex = index;
      bestSegmentFraction = fraction;
      bestCompletedLength = completedLength;
    }
    completedLength += segmentLengths[index] ?? 0;
  }

  const projectedLength =
    bestCompletedLength + (segmentLengths[bestSegmentIndex] ?? 0) * bestSegmentFraction;
  return {
    distanceKm: Math.sqrt(bestDistanceSquared),
    progress: totalLength === 0 ? 0 : projectedLength / totalLength,
    segmentIndex: bestSegmentIndex,
    segmentFraction: bestSegmentFraction,
  };
}

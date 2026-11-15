(() => {
  "use strict";

  const cache = new Map();

  function loadGeoJson(url) {
    if (!cache.has(url)) {
      cache.set(url, fetch(url).then(response => {
        if (!response.ok) {
          throw new Error(`Failed to load geographic dataset: ${response.status}`);
        }
        return response.json();
      }));
    }
    return cache.get(url);
  }

  function normalizeLongitude(longitude) {
    let value = longitude;
    while (value < -180) value += 360;
    while (value > 180) value -= 360;
    return value;
  }

  function coordinateForPoint(longitude, pointLongitude) {
    let value = longitude;
    while (value - pointLongitude > 180) value -= 360;
    while (value - pointLongitude < -180) value += 360;
    return value;
  }

  function unwrapRing(longitude, ring) {
    const unwrapped = [];
    let previousLongitude = null;
    ring.forEach(point => {
      let currentLongitude = Number(point[0]);
      if (previousLongitude === null) {
        currentLongitude = coordinateForPoint(currentLongitude, longitude);
      } else {
        while (currentLongitude - previousLongitude > 180) currentLongitude -= 360;
        while (currentLongitude - previousLongitude < -180) currentLongitude += 360;
      }
      unwrapped.push([currentLongitude, Number(point[1])]);
      previousLongitude = currentLongitude;
    });
    return unwrapped;
  }

  function pointInRing(longitude, latitude, ring) {
    const unwrappedRing = unwrapRing(longitude, ring);
    let inside = false;
    for (let index = 0, previous = unwrappedRing.length - 1;
      index < unwrappedRing.length;
      previous = index++) {
      const currentPoint = unwrappedRing[index];
      const previousPoint = unwrappedRing[previous];
      const currentLongitude = currentPoint[0];
      const previousLongitude = previousPoint[0];
      const currentLatitude = currentPoint[1];
      const previousLatitude = previousPoint[1];

      const intersects = ((currentLatitude > latitude) !== (previousLatitude > latitude))
        && (longitude < (previousLongitude - currentLongitude)
          * (latitude - currentLatitude)
          / (previousLatitude - currentLatitude)
          + currentLongitude);
      if (intersects) inside = !inside;
    }
    return inside;
  }

  function pointInPolygon(longitude, latitude, rings) {
    if (!rings.length || !pointInRing(longitude, latitude, rings[0])) return false;
    return !rings.slice(1).some(ring => pointInRing(longitude, latitude, ring));
  }

  function pointInGeometry(longitude, latitude, geometry) {
    if (!geometry) return false;
    if (geometry.type === "Polygon") {
      return pointInPolygon(longitude, latitude, geometry.coordinates);
    }
    if (geometry.type === "MultiPolygon") {
      return geometry.coordinates.some(polygon => pointInPolygon(longitude, latitude, polygon));
    }
    return false;
  }

  function featureName(feature, ocean) {
    const properties = feature.properties || {};
    return ocean
      ? properties.name_en || properties.name || properties.label
      : properties.NAME_EN || properties.NAME_LONG || properties.NAME || properties.name;
  }

  function featureMatches(feature, longitude, latitude, ocean) {
    const geometry = feature.geometry;
    if (!geometry || !featureName(feature, ocean)) return false;
    return pointInGeometry(longitude, latitude, geometry);
  }

  function createGeoLocationLookup({
    countriesUrl = "/geography/ne_50m_admin_0_countries.geojson",
    oceansUrl = "/geography/ne_50m_geography_marine_polys.geojson",
  } = {}) {
    let datasetsPromise;

    async function load() {
      if (!datasetsPromise) {
        datasetsPromise = Promise.all([
          loadGeoJson(countriesUrl),
          loadGeoJson(oceansUrl),
        ]);
      }
      return datasetsPromise;
    }

    return {
      async lookup(latitude, longitude) {
        const numericLatitude = Number(latitude);
        const numericLongitude = normalizeLongitude(Number(longitude));
        if (!Number.isFinite(numericLatitude) || !Number.isFinite(numericLongitude)) {
          return null;
        }

        const [countries, oceans] = await load();
        const country = countries.features.find(feature =>
          featureMatches(feature, numericLongitude, numericLatitude, false));
        if (country) {
          return { name: featureName(country, false), kind: "country" };
        }

        const ocean = oceans.features.find(feature =>
          featureMatches(feature, numericLongitude, numericLatitude, true));
        return ocean
          ? { name: featureName(ocean, true), kind: "ocean" }
          : null;
      },
    };
  }

  window.createGeoLocationLookup = createGeoLocationLookup;
})();

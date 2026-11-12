import { MapPin, Plane } from "lucide-react";
import type { GameState, WorldDefinition, WorldLocation } from "../types/game";

interface RouteMapProps {
  state: GameState;
  world: WorldDefinition;
}

function MapNode({ location, state }: { location: WorldLocation; state: GameState }) {
  const current = state.location === location.id;
  const discovered = state.discovered_locations.includes(location.id);
  return (
    <li className={`map-node ${current ? "map-current" : ""} ${discovered ? "map-discovered" : ""}`}>
      <span className="map-dot">{location.is_destination ? <Plane size={13} /> : current ? <MapPin size={13} /> : null}</span>
      <div><strong>{location.label}</strong><small>{current ? "You are here" : location.is_destination ? "Destination" : discovered ? "Discovered" : "Unknown"}</small></div>
    </li>
  );
}

export function RouteMap({ state, world }: RouteMapProps) {
  const main = world.locations.filter((location) => location.lane === "main").sort((a, b) => a.order - b.order);
  const alternate = world.locations.filter((location) => location.lane === "alternate").sort((a, b) => a.order - b.order);
  const current = world.locations.find((location) => location.id === state.location);
  const onwardConnections = world.routes.filter((route) => route.origin === state.location).length;
  const progress = current?.progress ?? 0;

  return (
    <section className="map-panel" aria-labelledby="route-title">
      <div className="panel-heading">
        <div id="route-title">Route intelligence</div>
        <span>World v{world.version}</span>
      </div>
      <div className="map-canvas">
        <ol className="map-route map-route-main">
          {main.map((location) => <MapNode key={location.id} location={location} state={state} />)}
        </ol>
        <div className="branch-label">Alternate corridor</div>
        <ol className="map-route map-route-side">
          {alternate.map((location) => <MapNode key={location.id} location={location} state={state} />)}
        </ol>
      </div>
      <div className="map-legend">
        <span><i className="legend-current" /> Current</span>
        <span><i className="legend-seen" /> Discovered</span>
        <span><i /> Unknown</span>
        <span>{onwardConnections} onward connection{onwardConnections === 1 ? "" : "s"}</span>
      </div>
      <div className="route-progress" aria-label={`${progress} percent route progress`}>
        <div><span>Terminal progress</span><strong>{progress}%</strong></div>
        <i><b style={{ width: `${progress}%` }} /></i>
      </div>
    </section>
  );
}

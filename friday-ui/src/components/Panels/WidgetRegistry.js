import { lazy } from 'react';

/**
 * WidgetRegistry — Modular registry for dashboard HUD widgets.
 * Allows widgets to be lazy-loaded on demand and easily registered/toggled.
 */

export const WIDGET_REGISTRY = {
  spotify: {
    id: 'spotify',
    title: 'Spotify Player',
    component: lazy(() => import('./SpotifyCard')),
  },
  todos: {
    id: 'todos',
    title: 'Tasks & Reminders',
    component: lazy(() => import('./TodoCard')),
  },
  weather: {
    id: 'weather',
    title: 'Live Weather',
    component: lazy(() => import('./WeatherCard')),
  },
  system: {
    id: 'system',
    title: 'Hardware Telemetry',
    component: lazy(() => import('./SystemMonitorCard')),
  },
  search: {
    id: 'search',
    title: 'Web Search',
    component: lazy(() => import('./WebSearchCard')),
  },
};

export const DEFAULT_ACTIVE_WIDGETS = ['spotify', 'todos', 'weather', 'system', 'search'];

// Export all components from the stats module
export { StatsManager } from './stats-manager.js';
export { ChartManager } from './ChartManager.js';
export { TableManager } from './TableManager.js';
export { StatsLoader } from './StatsLoader.js';

// Main StatsManager is also the default export
export { StatsManager as default } from './stats-manager.js';

// This index.js file allows for more convenient imports:
// import { StatsManager } from '../stats/index.js';
// or even:
// import { StatsManager } from '../stats';

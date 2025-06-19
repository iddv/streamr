import { DeploymentContext, StageConfig, RegionConfig } from './types';
import { streamrConfig } from './streamr-config';

export function createDeploymentContext(stage: string, region: string): DeploymentContext {
  const stageConfig = streamrConfig.stages[stage];
  const regionConfig = streamrConfig.regions[region];

  if (!stageConfig) {
    throw new Error(`Unknown stage: ${stage}. Available stages: ${Object.keys(streamrConfig.stages).join(', ')}`);
  }

  if (!regionConfig) {
    throw new Error(`Unknown region: ${region}. Available regions: ${Object.keys(streamrConfig.regions).join(', ')}`);
  }

  return {
    stage,
    region,
    stageConfig,
    regionConfig,
    stackName: (suffix: string) => `${streamrConfig.app.name}-${stage}-${regionConfig.name}-${suffix}`,
    resourceName: (name: string) => `${streamrConfig.app.name}-${stage}-${name}`,
  };
}

export function getValidStages(): string[] {
  return Object.keys(streamrConfig.stages);
}

export function getValidRegions(): string[] {
  return Object.keys(streamrConfig.regions);
}

export function getPrimaryRegion(): string {
  const primaryRegion = Object.values(streamrConfig.regions).find(r => r.isPrimary);
  if (!primaryRegion) {
    throw new Error('No primary region configured');
  }
  return primaryRegion.region;
} 
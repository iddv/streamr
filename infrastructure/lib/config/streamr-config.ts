import { StreamrConfig } from './types';

export const streamrConfig: StreamrConfig = {
  app: {
    name: 'streamr-p2p',
    version: '0.1.0',
    owner: 'streamr-team',
  },

  stages: {
    beta: {
      name: 'beta',
      description: 'Beta stage for experiments and iterative changes',
      isProd: false,
      enableDeletionProtection: false,
      enableBackups: false,
      instanceSize: 'micro',
      multiAz: false,
      monitoring: {
        detailed: false,
        alarms: false,
      },
    },
    gamma: {
      name: 'gamma',
      description: 'Gamma stage for pre-prod stable continuous testing (friends testing)',
      isProd: false,
      enableDeletionProtection: true,
      enableBackups: true,
      instanceSize: 'small',
      multiAz: false,
      monitoring: {
        detailed: true,
        alarms: true,
      },
    },
    prod: {
      name: 'prod',
      description: 'Production stage for live operations',
      isProd: true,
      enableDeletionProtection: true,
      enableBackups: true,
      instanceSize: 'medium',
      multiAz: true,
      monitoring: {
        detailed: true,
        alarms: true,
      },
    },
  },

  regions: {
    'eu-west-1': {
      region: 'eu-west-1',
      name: 'ireland',
      isPrimary: true,
      availabilityZones: 2,
    },
    'us-east-1': {
      region: 'us-east-1',
      name: 'virginia',
      isPrimary: false,
      availabilityZones: 3,
    },
    'ap-southeast-1': {
      region: 'ap-southeast-1',
      name: 'singapore',
      isPrimary: false,
      availabilityZones: 3,
    },
  },

  networking: {
    vpcCidr: '10.0.0.0/16',
    enableNatGateway: false, // Cost optimization for beta/gamma
  },

  database: {
    engine: 'postgres',
    version: '15.13',
    port: 5432,
  },

  cache: {
    engine: 'redis',
    port: 6379,
  },
}; 
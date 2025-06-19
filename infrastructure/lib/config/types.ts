export interface StageConfig {
  readonly name: string;
  readonly description: string;
  readonly isProd: boolean;
  readonly enableDeletionProtection: boolean;
  readonly enableBackups: boolean;
  readonly instanceSize: 'micro' | 'small' | 'medium' | 'large';
  readonly multiAz: boolean;
  readonly monitoring: {
    readonly detailed: boolean;
    readonly alarms: boolean;
  };
}

export interface RegionConfig {
  readonly region: string;
  readonly name: string;
  readonly isPrimary: boolean;
  readonly availabilityZones: number;
}

export interface StreamrConfig {
  readonly app: {
    readonly name: string;
    readonly version: string;
    readonly owner: string;
  };
  readonly stages: Record<string, StageConfig>;
  readonly regions: Record<string, RegionConfig>;
  readonly networking: {
    readonly vpcCidr: string;
    readonly enableNatGateway: boolean;
  };
  readonly database: {
    readonly engine: string;
    readonly version: string;
    readonly port: number;
  };
  readonly cache: {
    readonly engine: string;
    readonly port: number;
  };
}

export interface DeploymentContext {
  readonly stage: string;
  readonly region: string;
  readonly stageConfig: StageConfig;
  readonly regionConfig: RegionConfig;
  readonly stackName: (suffix: string) => string;
  readonly resourceName: (name: string) => string;
} 
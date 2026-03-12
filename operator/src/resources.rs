//! K8s resource builders — generic across all chains.
//!
//! Builds StatefulSet, Services, ConfigMaps, RBAC, and PDB from Cluster spec.
//! Chain-specific behavior is injected via the ChainDriver trait.

use crate::crd::{Cluster, PortMapping};
use crate::drivers::ChainDriver;
use crate::error::Result;
use k8s_openapi::api::apps::v1::{
    StatefulSet, StatefulSetPersistentVolumeClaimRetentionPolicy, StatefulSetSpec,
};
use k8s_openapi::api::core::v1::{
    ConfigMap, Container, ContainerPort, EnvVar, LocalObjectReference,
    PersistentVolumeClaim, PersistentVolumeClaimSpec, PodSecurityContext, PodSpec,
    PodTemplateSpec, Probe, ResourceRequirements, SecretVolumeSource, Service, ServicePort,
    ServiceSpec as K8sServiceSpec, Volume, VolumeMount,
};
use k8s_openapi::api::policy::v1::{PodDisruptionBudget, PodDisruptionBudgetSpec};
use k8s_openapi::api::rbac::v1::{PolicyRule, Role, RoleBinding, RoleRef, Subject};
use k8s_openapi::apimachinery::pkg::api::resource::Quantity;
use k8s_openapi::apimachinery::pkg::apis::meta::v1::{LabelSelector, OwnerReference};
use k8s_openapi::apimachinery::pkg::util::intstr::IntOrString;
use kube::{Resource, ResourceExt};
use std::collections::BTreeMap;

// ─── Labels & Owner Refs ───

pub fn resource_labels(name: &str, chain: &str) -> BTreeMap<String, String> {
    let mut labels = BTreeMap::new();
    labels.insert("app.kubernetes.io/name".into(), chain.to_string());
    labels.insert("app.kubernetes.io/instance".into(), name.to_string());
    labels.insert("app.kubernetes.io/managed-by".into(), "bootnode-operator".into());
    labels
}

pub fn owner_reference(cluster: &Cluster) -> OwnerReference {
    OwnerReference {
        api_version: Cluster::api_version(&()).to_string(),
        kind: Cluster::kind(&()).to_string(),
        name: cluster.name_any(),
        uid: cluster.metadata.uid.clone().unwrap_or_default(),
        controller: Some(true),
        block_owner_deletion: Some(true),
    }
}

fn resolve_ports(cluster: &Cluster, driver: &dyn ChainDriver) -> Vec<PortMapping> {
    if cluster.spec.ports.is_empty() {
        driver.default_ports()
    } else {
        cluster.spec.ports.clone()
    }
}

fn port_by_name(ports: &[PortMapping], name: &str) -> Option<i32> {
    ports.iter().find(|p| p.name == name).map(|p| p.port)
}

fn build_resource_requirements(spec: &crate::crd::ResourceSpec) -> ResourceRequirements {
    let mut requests = BTreeMap::new();
    let mut limits = BTreeMap::new();

    requests.insert("cpu".into(), Quantity(spec.cpu_request.clone().unwrap_or_else(|| "500m".into())));
    requests.insert("memory".into(), Quantity(spec.memory_request.clone().unwrap_or_else(|| "1Gi".into())));
    limits.insert("cpu".into(), Quantity(spec.cpu_limit.clone().unwrap_or_else(|| "2".into())));
    limits.insert("memory".into(), Quantity(spec.memory_limit.clone().unwrap_or_else(|| "4Gi".into())));

    ResourceRequirements {
        requests: Some(requests),
        limits: Some(limits),
        ..Default::default()
    }
}

// ─── ConfigMap ───

pub fn build_config_map(cluster: &Cluster) -> ConfigMap {
    let name = cluster.name_any();
    let namespace = cluster.namespace().unwrap_or_else(|| "default".into());
    let labels = resource_labels(&name, &cluster.spec.chain);

    let mut data = BTreeMap::new();

    // Config overrides
    if !cluster.spec.config.is_empty() {
        let config_json = serde_json::to_string_pretty(&cluster.spec.config).unwrap_or_default();
        data.insert("config.json".into(), config_json);
    }

    // Inline genesis
    if let Some(genesis) = &cluster.spec.genesis {
        let genesis_json = serde_json::to_string_pretty(genesis).unwrap_or_default();
        data.insert("genesis.json".into(), genesis_json);
    }

    ConfigMap {
        metadata: kube::core::ObjectMeta {
            name: Some(format!("{}-config", name)),
            namespace: Some(namespace),
            labels: Some(labels),
            owner_references: Some(vec![owner_reference(cluster)]),
            ..Default::default()
        },
        data: Some(data),
        ..Default::default()
    }
}

pub fn build_startup_configmap(cluster: &Cluster, script: String) -> ConfigMap {
    let name = cluster.name_any();
    let namespace = cluster.namespace().unwrap_or_else(|| "default".into());
    let labels = resource_labels(&name, &cluster.spec.chain);

    let mut data = BTreeMap::new();
    data.insert("startup.sh".into(), script);

    ConfigMap {
        metadata: kube::core::ObjectMeta {
            name: Some(format!("{}-startup", name)),
            namespace: Some(namespace),
            labels: Some(labels),
            owner_references: Some(vec![owner_reference(cluster)]),
            ..Default::default()
        },
        data: Some(data),
        ..Default::default()
    }
}

// ─── Services ───

pub fn build_headless_service(cluster: &Cluster, driver: &dyn ChainDriver) -> Service {
    let name = cluster.name_any();
    let namespace = cluster.namespace().unwrap_or_else(|| "default".into());
    let labels = resource_labels(&name, &cluster.spec.chain);
    let ports = resolve_ports(cluster, driver);

    Service {
        metadata: kube::core::ObjectMeta {
            name: Some(format!("{}-headless", name)),
            namespace: Some(namespace),
            labels: Some(labels.clone()),
            owner_references: Some(vec![owner_reference(cluster)]),
            ..Default::default()
        },
        spec: Some(K8sServiceSpec {
            cluster_ip: Some("None".into()),
            selector: Some(labels),
            ports: Some(ports.iter().map(|p| ServicePort {
                name: Some(p.name.clone()),
                port: p.port,
                target_port: Some(IntOrString::Int(p.port)),
                ..Default::default()
            }).collect()),
            publish_not_ready_addresses: Some(true),
            ..Default::default()
        }),
        ..Default::default()
    }
}

pub fn build_rpc_service(cluster: &Cluster, driver: &dyn ChainDriver) -> Service {
    let name = cluster.name_any();
    let namespace = cluster.namespace().unwrap_or_else(|| "default".into());
    let labels = resource_labels(&name, &cluster.spec.chain);
    let ports = resolve_ports(cluster, driver);

    let mut annotations = cluster.spec.service.annotations.clone();
    annotations.insert(
        "service.beta.kubernetes.io/do-loadbalancer-name".into(),
        format!("k8s-{}", name),
    );

    Service {
        metadata: kube::core::ObjectMeta {
            name: Some(name.clone()),
            namespace: Some(namespace),
            labels: Some(labels.clone()),
            annotations: Some(annotations),
            owner_references: Some(vec![owner_reference(cluster)]),
            ..Default::default()
        },
        spec: Some(K8sServiceSpec {
            type_: Some(cluster.spec.service.service_type.clone()),
            selector: Some(labels),
            ports: Some(ports.iter().map(|p| ServicePort {
                name: Some(p.name.clone()),
                port: p.port,
                target_port: Some(IntOrString::Int(p.port)),
                ..Default::default()
            }).collect()),
            ..Default::default()
        }),
        ..Default::default()
    }
}

pub fn build_per_pod_service(
    cluster: &Cluster,
    driver: &dyn ChainDriver,
    index: u32,
) -> Service {
    let name = cluster.name_any();
    let namespace = cluster.namespace().unwrap_or_else(|| "default".into());
    let svc_name = format!("{}-{}", name, index);
    let ports = resolve_ports(cluster, driver);

    let mut labels = resource_labels(&name, &cluster.spec.chain);
    labels.insert("pod-index".into(), index.to_string());

    let mut selector = BTreeMap::new();
    selector.insert("app.kubernetes.io/name".into(), cluster.spec.chain.clone());
    selector.insert("app.kubernetes.io/instance".into(), name.clone());
    selector.insert("statefulset.kubernetes.io/pod-name".into(), format!("{}-{}", name, index));

    let mut annotations = cluster.spec.service.annotations.clone();
    annotations.insert(
        "service.beta.kubernetes.io/do-loadbalancer-name".into(),
        format!("k8s-{}-{}-{}", name, cluster.spec.network, index),
    );

    Service {
        metadata: kube::core::ObjectMeta {
            name: Some(svc_name),
            namespace: Some(namespace),
            labels: Some(labels),
            annotations: Some(annotations),
            owner_references: Some(vec![owner_reference(cluster)]),
            ..Default::default()
        },
        spec: Some(K8sServiceSpec {
            type_: Some("LoadBalancer".into()),
            selector: Some(selector),
            ports: Some(ports.iter().map(|p| ServicePort {
                name: Some(p.name.clone()),
                port: p.port,
                target_port: Some(IntOrString::Int(p.port)),
                ..Default::default()
            }).collect()),
            ..Default::default()
        }),
        ..Default::default()
    }
}

// ─── RBAC ───

pub fn build_role(cluster: &Cluster) -> Role {
    let name = cluster.name_any();
    let namespace = cluster.namespace().unwrap_or_else(|| "default".into());

    Role {
        metadata: kube::core::ObjectMeta {
            name: Some(format!("{}-service-reader", name)),
            namespace: Some(namespace),
            owner_references: Some(vec![owner_reference(cluster)]),
            ..Default::default()
        },
        rules: Some(vec![PolicyRule {
            api_groups: Some(vec!["".into()]),
            resources: Some(vec!["services".into()]),
            verbs: vec!["get".into()],
            ..Default::default()
        }]),
    }
}

pub fn build_role_binding(cluster: &Cluster) -> RoleBinding {
    let name = cluster.name_any();
    let namespace = cluster.namespace().unwrap_or_else(|| "default".into());
    let role_name = format!("{}-service-reader", name);

    RoleBinding {
        metadata: kube::core::ObjectMeta {
            name: Some(role_name.clone()),
            namespace: Some(namespace.clone()),
            owner_references: Some(vec![owner_reference(cluster)]),
            ..Default::default()
        },
        role_ref: RoleRef {
            api_group: "rbac.authorization.k8s.io".into(),
            kind: "Role".into(),
            name: role_name,
        },
        subjects: Some(vec![Subject {
            kind: "ServiceAccount".into(),
            name: "default".into(),
            namespace: Some(namespace),
            ..Default::default()
        }]),
    }
}

// ─── PDB ───

pub fn build_pdb(cluster: &Cluster) -> PodDisruptionBudget {
    let name = cluster.name_any();
    let namespace = cluster.namespace().unwrap_or_else(|| "default".into());
    let labels = resource_labels(&name, &cluster.spec.chain);

    PodDisruptionBudget {
        metadata: kube::core::ObjectMeta {
            name: Some(format!("{}-pdb", name)),
            namespace: Some(namespace),
            owner_references: Some(vec![owner_reference(cluster)]),
            ..Default::default()
        },
        spec: Some(PodDisruptionBudgetSpec {
            max_unavailable: Some(IntOrString::Int(1)),
            selector: Some(LabelSelector {
                match_labels: Some(labels),
                ..Default::default()
            }),
            ..Default::default()
        }),
        ..Default::default()
    }
}

// ─── StatefulSet ───

pub fn build_statefulset(
    cluster: &Cluster,
    driver: &dyn ChainDriver,
) -> Result<StatefulSet> {
    let name = cluster.name_any();
    let namespace = cluster.namespace().unwrap_or_else(|| "default".into());
    let spec = &cluster.spec;
    let labels = resource_labels(&name, &spec.chain);
    let ports = resolve_ports(cluster, driver);
    let resources = build_resource_requirements(&spec.resources);

    // Health check port
    let health = if spec.health == crate::crd::HealthSpec::default() {
        driver.default_health()
    } else {
        spec.health.clone()
    };
    let health_port = port_by_name(&ports, &health.port_name)
        .unwrap_or_else(|| ports.first().map(|p| p.port).unwrap_or(8080));

    // Volumes
    let startup_cm = spec.startup_script.clone().unwrap_or_else(|| format!("{}-startup", name));
    let mut volumes = vec![
        Volume {
            name: "config".into(),
            config_map: Some(k8s_openapi::api::core::v1::ConfigMapVolumeSource {
                name: Some(format!("{}-config", name)),
                ..Default::default()
            }),
            ..Default::default()
        },
        Volume {
            name: "startup-script".into(),
            config_map: Some(k8s_openapi::api::core::v1::ConfigMapVolumeSource {
                name: Some(startup_cm),
                default_mode: Some(0o755),
                ..Default::default()
            }),
            ..Default::default()
        },
    ];

    let mut volume_mounts = vec![
        VolumeMount { name: "data".into(), mount_path: "/data".into(), ..Default::default() },
        VolumeMount { name: "startup-script".into(), mount_path: "/scripts".into(), ..Default::default() },
    ];

    // Genesis volume
    if spec.genesis.is_some() {
        volume_mounts.push(VolumeMount {
            name: "genesis".into(), mount_path: "/genesis".into(),
            read_only: Some(true), ..Default::default()
        });
        volumes.push(Volume {
            name: "genesis".into(),
            config_map: Some(k8s_openapi::api::core::v1::ConfigMapVolumeSource {
                name: Some(format!("{}-config", name)),
                ..Default::default()
            }),
            ..Default::default()
        });
    } else if let Some(genesis_cm) = &spec.genesis_config_map {
        volume_mounts.push(VolumeMount {
            name: "genesis".into(), mount_path: "/genesis".into(),
            read_only: Some(true), ..Default::default()
        });
        volumes.push(Volume {
            name: "genesis".into(),
            config_map: Some(k8s_openapi::api::core::v1::ConfigMapVolumeSource {
                name: Some(genesis_cm.clone()),
                ..Default::default()
            }),
            ..Default::default()
        });
    }

    // Staking keys volume
    if let Some(staking) = &spec.staking {
        volumes.push(Volume {
            name: "staking-keys".into(),
            secret: Some(SecretVolumeSource {
                secret_name: Some(staking.secret_name.clone()),
                ..Default::default()
            }),
            ..Default::default()
        });
        volume_mounts.push(VolumeMount {
            name: "staking-keys".into(), mount_path: "/staking-keys".into(),
            read_only: Some(true), ..Default::default()
        });
    }

    // Env vars from driver
    let mut env = vec![
        EnvVar {
            name: "POD_NAME".into(),
            value_from: Some(k8s_openapi::api::core::v1::EnvVarSource {
                field_ref: Some(k8s_openapi::api::core::v1::ObjectFieldSelector {
                    field_path: "metadata.name".into(),
                    ..Default::default()
                }),
                ..Default::default()
            }),
            ..Default::default()
        },
    ];
    for (k, v) in driver.env_vars(cluster) {
        env.push(EnvVar { name: k, value: Some(v), ..Default::default() });
    }

    // Main container
    let container = Container {
        name: driver.container_name().into(),
        image: Some(format!("{}:{}", spec.image.repository, spec.image.tag)),
        image_pull_policy: Some(spec.image.pull_policy.clone()),
        command: Some(vec!["/bin/sh".into(), "/scripts/startup.sh".into()]),
        ports: Some(ports.iter().map(|p| ContainerPort {
            name: Some(p.name.clone()),
            container_port: p.port,
            ..Default::default()
        }).collect()),
        env: Some(env),
        volume_mounts: Some(volume_mounts.clone()),
        resources: Some(resources),
        startup_probe: Some(Probe {
            tcp_socket: Some(k8s_openapi::api::core::v1::TCPSocketAction {
                port: IntOrString::Int(health_port),
                ..Default::default()
            }),
            initial_delay_seconds: Some(5),
            period_seconds: Some(10),
            failure_threshold: Some(30),
            ..Default::default()
        }),
        liveness_probe: Some(Probe {
            http_get: Some(k8s_openapi::api::core::v1::HTTPGetAction {
                path: Some(health.path.clone()),
                port: IntOrString::Int(health_port),
                ..Default::default()
            }),
            period_seconds: Some(15),
            failure_threshold: Some(3),
            timeout_seconds: Some(5),
            ..Default::default()
        }),
        readiness_probe: Some(Probe {
            http_get: Some(k8s_openapi::api::core::v1::HTTPGetAction {
                path: Some(health.path),
                port: IntOrString::Int(health_port),
                ..Default::default()
            }),
            period_seconds: Some(10),
            failure_threshold: Some(3),
            timeout_seconds: Some(5),
            ..Default::default()
        }),
        ..Default::default()
    };

    // Init containers
    let mut init_containers = Vec::new();

    // Startup gate
    let gate = &spec.startup_gate;
    if gate.enabled && spec.replicas > 1 {
        let gate_script = driver.startup_gate_script(cluster)?;
        init_containers.push(Container {
            name: "startup-gate".into(),
            image: Some(format!("{}:{}", spec.image.repository, spec.image.tag)),
            image_pull_policy: Some(spec.image.pull_policy.clone()),
            command: Some(vec!["/bin/sh".into(), "-c".into()]),
            args: Some(vec![gate_script]),
            ..Default::default()
        });
    }

    // Driver init script
    if let Some(init_script) = driver.init_script(cluster)? {
        let init_image = spec.init.as_ref()
            .map(|i| i.image.clone())
            .unwrap_or_else(|| format!("{}:{}", spec.image.repository, spec.image.tag));

        let mut init_vm = vec![
            VolumeMount { name: "data".into(), mount_path: "/data".into(), ..Default::default() },
        ];
        if spec.staking.is_some() {
            init_vm.push(VolumeMount {
                name: "staking-keys".into(), mount_path: "/staking-keys".into(),
                read_only: Some(true), ..Default::default()
            });
        }

        init_containers.push(Container {
            name: "init-plugins".into(),
            image: Some(init_image),
            image_pull_policy: Some(spec.init.as_ref().map(|i| i.pull_policy.clone()).unwrap_or_else(|| "IfNotPresent".into())),
            security_context: Some(k8s_openapi::api::core::v1::SecurityContext {
                run_as_user: Some(0),
                run_as_group: Some(0),
                ..Default::default()
            }),
            command: Some(vec!["/bin/sh".into(), "-c".into()]),
            args: Some(vec![init_script]),
            volume_mounts: Some(init_vm),
            ..Default::default()
        });
    }

    // PVC template
    let pvc_template = PersistentVolumeClaim {
        metadata: kube::core::ObjectMeta {
            name: Some("data".into()),
            ..Default::default()
        },
        spec: Some(PersistentVolumeClaimSpec {
            access_modes: Some(vec!["ReadWriteOnce".into()]),
            storage_class_name: spec.storage.storage_class.clone(),
            resources: Some(ResourceRequirements {
                requests: Some({
                    let mut m = BTreeMap::new();
                    m.insert("storage".into(), Quantity(spec.storage.size.clone()));
                    m
                }),
                ..Default::default()
            }),
            ..Default::default()
        }),
        ..Default::default()
    };

    let pull_secrets: Option<Vec<LocalObjectReference>> = if spec.image.pull_secrets.is_empty() {
        None
    } else {
        Some(spec.image.pull_secrets.iter().map(|s| LocalObjectReference { name: Some(s.clone()) }).collect())
    };

    let update_strategy = match spec.upgrade_strategy.strategy_type.as_str() {
        "RollingUpdate" => k8s_openapi::api::apps::v1::StatefulSetUpdateStrategy {
            type_: Some("RollingUpdate".into()),
            ..Default::default()
        },
        _ => k8s_openapi::api::apps::v1::StatefulSetUpdateStrategy {
            type_: Some("OnDelete".into()),
            ..Default::default()
        },
    };

    Ok(StatefulSet {
        metadata: kube::core::ObjectMeta {
            name: Some(name.clone()),
            namespace: Some(namespace),
            labels: Some(labels.clone()),
            annotations: Some({
                let mut a = BTreeMap::new();
                a.insert("bootnode.dev/protect-pvc".into(), "true".into());
                a
            }),
            owner_references: Some(vec![owner_reference(cluster)]),
            ..Default::default()
        },
        spec: Some(StatefulSetSpec {
            replicas: Some(spec.replicas as i32),
            selector: LabelSelector { match_labels: Some(labels.clone()), ..Default::default() },
            service_name: format!("{}-headless", name),
            template: PodTemplateSpec {
                metadata: Some(kube::core::ObjectMeta { labels: Some(labels), ..Default::default() }),
                spec: Some(PodSpec {
                    security_context: Some(PodSecurityContext {
                        fs_group: Some(spec.security.fs_group),
                        run_as_user: Some(spec.security.run_as_user),
                        run_as_group: Some(spec.security.run_as_group),
                        ..Default::default()
                    }),
                    init_containers: if init_containers.is_empty() { None } else { Some(init_containers) },
                    containers: vec![container],
                    volumes: Some(volumes),
                    image_pull_secrets: pull_secrets,
                    termination_grace_period_seconds: Some(30),
                    ..Default::default()
                }),
            },
            volume_claim_templates: Some(vec![pvc_template]),
            pod_management_policy: Some("Parallel".into()),
            update_strategy: Some(update_strategy),
            persistent_volume_claim_retention_policy: Some(
                StatefulSetPersistentVolumeClaimRetentionPolicy {
                    when_deleted: Some("Retain".into()),
                    when_scaled: Some("Retain".into()),
                },
            ),
            ..Default::default()
        }),
        ..Default::default()
    })
}

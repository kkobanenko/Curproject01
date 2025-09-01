{{/*
Expand the name of the chart.
*/}}
{{- define "rag-platform.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "rag-platform.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "rag-platform.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "rag-platform.labels" -}}
helm.sh/chart: {{ include "rag-platform.chart" . }}
{{ include "rag-platform.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: rag-platform
{{- end }}

{{/*
Selector labels
*/}}
{{- define "rag-platform.selectorLabels" -}}
app.kubernetes.io/name: {{ include "rag-platform.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "rag-platform.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "rag-platform.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Generate secrets
*/}}
{{- define "rag-platform.secretName" -}}
{{ include "rag-platform.fullname" . }}-secrets
{{- end }}

{{/*
Generate random secrets
*/}}
{{- define "rag-platform.generateSecret" -}}
{{- if .Values.secrets.generate.enabled }}
{{- randAlphaNum .Values.secrets.generate.length | b64enc }}
{{- else }}
{{- required "Secret value is required when secrets.generate.enabled is false" . }}
{{- end }}
{{- end }}

{{/*
Database URL
*/}}
{{- define "rag-platform.databaseUrl" -}}
{{- if .Values.postgresql.enabled }}
postgresql://{{ .Values.postgresql.auth.username }}:{{ .Values.postgresql.auth.password }}@{{ include "rag-platform.fullname" . }}-postgresql:5432/{{ .Values.postgresql.auth.database }}
{{- else }}
{{- required "External database URL is required when postgresql.enabled is false" .Values.externalDatabase.url }}
{{- end }}
{{- end }}

{{/*
Redis URL
*/}}
{{- define "rag-platform.redisUrl" -}}
{{- if .Values.redis.enabled }}
redis://{{ include "rag-platform.fullname" . }}-redis-master:6379/0
{{- else }}
{{- required "External Redis URL is required when redis.enabled is false" .Values.externalRedis.url }}
{{- end }}
{{- end }}

{{/*
ClickHouse URL
*/}}
{{- define "rag-platform.clickhouseUrl" -}}
{{- if .Values.clickhouse.enabled }}
http://{{ include "rag-platform.fullname" . }}-clickhouse:8123
{{- else }}
{{- required "External ClickHouse URL is required when clickhouse.enabled is false" .Values.externalClickhouse.url }}
{{- end }}
{{- end }}

{{/*
Ingress hostname
*/}}
{{- define "rag-platform.ingressHost" -}}
{{- if .Values.global.domain }}
{{- .Values.global.domain }}
{{- else }}
{{- printf "%s.%s.svc.cluster.local" (include "rag-platform.fullname" .) .Release.Namespace }}
{{- end }}
{{- end }}

{{/*
API URL
*/}}
{{- define "rag-platform.apiUrl" -}}
{{- if .Values.ingress.enabled }}
https://{{ include "rag-platform.ingressHost" . }}/api
{{- else }}
http://{{ include "rag-platform.fullname" . }}-api:{{ .Values.api.service.port }}
{{- end }}
{{- end }}

{{/*
Resource limits helper
*/}}
{{- define "rag-platform.resources" -}}
{{- if . }}
resources:
  {{- if .requests }}
  requests:
    {{- if .requests.cpu }}
    cpu: {{ .requests.cpu }}
    {{- end }}
    {{- if .requests.memory }}
    memory: {{ .requests.memory }}
    {{- end }}
  {{- end }}
  {{- if .limits }}
  limits:
    {{- if .limits.cpu }}
    cpu: {{ .limits.cpu }}
    {{- end }}
    {{- if .limits.memory }}
    memory: {{ .limits.memory }}
    {{- end }}
  {{- end }}
{{- end }}
{{- end }}

{{/*
Security context helper
*/}}
{{- define "rag-platform.securityContext" -}}
{{- with .Values.security.securityContext }}
securityContext:
  {{- toYaml . | nindent 2 }}
{{- end }}
{{- end }}

{{/*
Pod anti-affinity helper
*/}}
{{- define "rag-platform.podAntiAffinity" -}}
podAntiAffinity:
  preferredDuringSchedulingIgnoredDuringExecution:
  - weight: 100
    podAffinityTerm:
      labelSelector:
        matchExpressions:
        - key: app.kubernetes.io/name
          operator: In
          values:
          - {{ include "rag-platform.name" . }}
        - key: app.kubernetes.io/component
          operator: In
          values:
          - {{ . }}
      topologyKey: kubernetes.io/hostname
{{- end }}

{{/*
Environment variables helper
*/}}
{{- define "rag-platform.env" -}}
{{- range $key, $value := . }}
- name: {{ $key }}
  value: {{ $value | quote }}
{{- end }}
{{- end }}

{{/*
Volume mounts helper
*/}}
{{- define "rag-platform.volumeMounts" -}}
{{- range . }}
- name: {{ .name }}
  mountPath: {{ .mountPath }}
  {{- if .subPath }}
  subPath: {{ .subPath }}
  {{- end }}
  {{- if .readOnly }}
  readOnly: {{ .readOnly }}
  {{- end }}
{{- end }}
{{- end }}

{{/*
Volumes helper
*/}}
{{- define "rag-platform.volumes" -}}
{{- range . }}
- name: {{ .name }}
  {{- if .emptyDir }}
  emptyDir: {}
  {{- else if .configMap }}
  configMap:
    name: {{ .configMap.name }}
    {{- if .configMap.items }}
    items:
    {{- range .configMap.items }}
    - key: {{ .key }}
      path: {{ .path }}
    {{- end }}
    {{- end }}
  {{- else if .secret }}
  secret:
    secretName: {{ .secret.name }}
    {{- if .secret.items }}
    items:
    {{- range .secret.items }}
    - key: {{ .key }}
      path: {{ .path }}
    {{- end }}
    {{- end }}
  {{- else if .persistentVolumeClaim }}
  persistentVolumeClaim:
    claimName: {{ .persistentVolumeClaim.claimName }}
  {{- end }}
{{- end }}
{{- end }}

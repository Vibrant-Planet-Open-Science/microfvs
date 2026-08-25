{{- define "microfvs.name" -}}
{{ .Values.nameOverride }}
{{- end -}}

{{- define "microfvs.labels" -}}
app.kubernetes.io/name: {{ include "microfvs.name" . }}
app.kubernetes.io/version: {{ required "image.tag is supplied by CI" .Values.image.tag | quote }}
app.kubernetes.io/managed-by: argocd
{{- end -}}

{{- define "microfvs.selectorLabels" -}}
app.kubernetes.io/name: {{ include "microfvs.name" . }}
{{- end -}}

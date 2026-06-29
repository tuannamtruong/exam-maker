flowchart TD
    A[Entwickler pusht Code nach GitHub] --> B[CodePipeline startet automatisch]

    B --> C[Source Stage<br/>GitHub über CodeStar Connection]
    C --> D[Build Stage<br/>AWS CodeBuild]

    D --> E[Abhängigkeiten installieren<br/>npm ci / yarn install]
    E --> F[Qualitätsprüfungen<br/>Linting, Unit Tests, Security Checks]
    F --> G[Frontend bauen<br/>npm run build]

    G --> H[Build-Artefakt speichern<br/>versionierter S3 Artifact Bucket]

    H --> I{Tests erfolgreich?}
    I -- Nein --> X[Pipeline stoppt<br/>Build Logs in CloudWatch]
    I -- Ja --> J[Manuelle Freigabe<br/>Approval Stage]

    J --> K{Freigegeben?}
    K -- Nein --> Y[Deployment abgebrochen]
    K -- Ja --> L[Deploy Stage<br/>Dateien in S3 Website Bucket hochladen]

    L --> M[Alte/entfernte Dateien bereinigen<br/>S3 sync --delete]
    M --> N[CloudFront Cache invalidieren<br/>CreateInvalidation]

    N --> O[Smoke Test / Health Check<br/>Website über CloudFront prüfen]
    O --> P{Prüfung erfolgreich?}

    P -- Nein --> R[Rollback<br/>vorheriges Artefakt erneut nach S3 deployen<br/>CloudFront invalidieren]
    P -- Ja --> Q[Release erfolgreich<br/>Benachrichtigung über SNS/Slack/Email]
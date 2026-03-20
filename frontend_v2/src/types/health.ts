type PipelineStageStatus = "yes" | "no";

interface PipelineStatusItem {
    stage: string;
    status: PipelineStageStatus;
}

export const pipelineStatus: PipelineStatusItem[] = [
    { stage: "Feature Extraction", status: "no" },
    { stage: "Temperature Scaling", status: "no" },
    { stage: "Predictions", status: "no" },
    { stage: "Routing", status: "no" },
];
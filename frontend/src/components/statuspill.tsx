import { IconCircleCheck, IconCircleX, IconCircle, IconCircleDashed } from "@tabler/icons-react";

type StepStatus = "queued" | "running" | "done" | "error";

type Step = {
  id: string;
  title: string;
  status: StepStatus;
  detail?: string;
};

const statusLabel: Record<StepStatus, string> = {
  queued: "Queued",
  running: "Running",
  done: "Done",
  error: "Error",
};

function StatusPill({ status }: { status: StepStatus }) {
  const getStatusClass = (status: StepStatus) => {
    switch (status) {
      case "done":
        return "text-emerald-600";
      case "error":
        return "text-destructive";
      default:
        return "text-muted-foreground";
    }
  };

  const style = "size-6 " + getStatusClass(status);

  return (
    <span className={style}>
      {status === "queued" && <IconCircle className={style} />}
      {status === "running" && <IconCircleDashed className={style} />}
      {status === "done" && <IconCircleCheck className={style} />}
      {status === "error" && <IconCircleX className={style} />}
    </span>
  );
}

export { StatusPill, statusLabel };
export type { Step, StepStatus };
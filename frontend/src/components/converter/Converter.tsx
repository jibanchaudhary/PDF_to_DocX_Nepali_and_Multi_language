import { AnimatePresence, motion } from "framer-motion";
import { useConversion } from "../../lib/useConversion";
import { SectionHeading } from "../ui/Reveal";
import { Uploader } from "./Uploader";
import { ProgressView } from "./ProgressView";
import { Results } from "./Results";
import { AlertTriangle, Refresh } from "../icons";

export function Converter() {
  const { state, convert, reset } = useConversion();

  return (
    <section id="convert" className="relative scroll-mt-24 py-24 md:py-32">
      <div className="pointer-events-none absolute inset-0 bloom opacity-70" />
      <div className="section relative">
        <SectionHeading
          eyebrow="Try it now"
          title={
            <>
              Convert a Nepali PDF to{" "}
              <span className="text-gradient">editable Word</span>
            </>
          }
          sub="Drop a file and watch PDFlow parse, route, recover and rebuild — then download the .docx."
        />

        <div className="mt-14">
          <div className="relative mx-auto max-w-4xl">
            <div className="glass rounded-5xl p-6 shadow-glass md:p-10">
              <AnimatePresence mode="wait">
                {state.phase === "idle" && (
                  <motion.div
                    key="upload"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0, scale: 0.98 }}
                    transition={{ duration: 0.3 }}
                  >
                    <Uploader onConvert={convert} />
                  </motion.div>
                )}

                {(state.phase === "uploading" ||
                  state.phase === "processing") && (
                  <motion.div
                    key="progress"
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.98 }}
                    transition={{ duration: 0.3 }}
                  >
                    <ProgressView state={state} />
                  </motion.div>
                )}

                {state.phase === "error" && (
                  <motion.div
                    key="error"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="mx-auto max-w-lg py-8 text-center"
                  >
                    <div className="mx-auto mb-4 grid h-14 w-14 place-items-center rounded-2xl bg-red-50 text-red-500">
                      <AlertTriangle className="h-7 w-7" />
                    </div>
                    <h3 className="text-xl font-semibold">Conversion failed</h3>
                    <p className="mx-auto mt-2 max-w-md text-ink-mute">
                      {state.error ??
                        "Something went wrong while processing your PDF."}
                    </p>
                    <button onClick={reset} className="btn-ghost mt-6">
                      <Refresh className="h-4 w-4" />
                      Try again
                    </button>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>

          {/* Results render outside the glass card so wide previews breathe */}
          <AnimatePresence>
            {state.phase === "done" && state.analysis && state.jobId && (
              <motion.div
                key="results"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="mx-auto mt-8 max-w-5xl"
              >
                <Results
                  jobId={state.jobId}
                  analysis={state.analysis}
                  onReset={reset}
                />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </section>
  );
}

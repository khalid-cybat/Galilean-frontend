import { useLocation } from "react-router-dom";

const pages = {
  "/": ["/legacy/", "SPHEREx mission home"],
  "/explorer": ["/legacy/explorer", "SPHEREx data explorer"],
  "/tracker": ["/legacy/tracker", "SPHEREx live tracker"],
  "/fits": ["/legacy/fits", "SPHEREx FITS viewer"],
};

export default function ExactApp() {
  const { pathname } = useLocation();
  const [source, title] = pages[pathname] || pages["/"];
  return (
    <iframe
      key={source}
      className="legacy-page"
      src={source}
      title={title}
      onLoad={(event) => {
        try {
          document.title = event.currentTarget.contentDocument.title;
        } catch {
          document.title = title;
        }
      }}
    />
  );
}
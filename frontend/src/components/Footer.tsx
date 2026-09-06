export default function Footer() {
  return (
    <footer className="ftr">
      <div className="shell ftr__inner">
        <span>
          Authentix — heuristic forensic analysis. A low score flags <em>inconsistency</em>, not proven
          forgery; a high score is not a guarantee of authenticity.
        </span>
        <span className="mono">analysed locally · nothing leaves this machine</span>
      </div>
    </footer>
  );
}

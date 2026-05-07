/* Kitchen teaser — single GIF, onion salad. */

function KitchenTeaser() {
  return (
    <div className="kt-wrap">
      <div className="kt-stage">
        <img
          src="assets/model_gifs/trial_21_onion.gif"
          alt="Onion salad"
          className="kt-gif"
        />
      </div>
    </div>
  );
}

window.KitchenTeaser = KitchenTeaser;

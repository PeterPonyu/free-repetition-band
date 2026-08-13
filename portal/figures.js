/* Consume the warehouse figure contract; never PeerJ FigureN.pdf paths. */
(function () {
  var status = document.getElementById("index-status");

  function setStatus(message) {
    if (status) {
      status.textContent = message;
    }
  }

  function markChapter() {
    var ids = ["band", "onset", "capacity", "exposure", "scale", "reproduce"];
    var items = document.querySelectorAll(".chapter-list li");
    var current = "band";
    var mid = window.scrollY + 120;
    ids.forEach(function (id) {
      var el = document.getElementById(id);
      if (el && el.offsetTop <= mid) {
        current = id;
      }
    });
    items.forEach(function (item) {
      var href = item.querySelector("a");
      var match = href && href.getAttribute("href") === "#" + current;
      item.classList.toggle("is-current", Boolean(match));
    });
  }

  fetch("./data/figures.json")
    .catch(function () {
      return fetch("../papers/FIGURE-INDEX.json");
    })
    .then(function (response) {
      if (!response || !response.ok) {
        throw new Error("missing");
      }
      return response.json();
    })
    .then(function (index) {
      window.__FIGURE_INDEX__ = index || null;
      if (!index || !index.figures) {
        setStatus("summary missing — see PIPELINE.md");
        return;
      }
      var ids = index.figures.map(function (fig) {
        return fig.id;
      });
      setStatus("FIGURE-INDEX loaded · " + ids.length + " plates · " + ids.join(" · "));
    })
    .catch(function () {
      window.__FIGURE_INDEX__ = null;
      setStatus("summary missing — see PIPELINE.md");
    });

  window.addEventListener("scroll", markChapter, { passive: true });
  markChapter();
})();

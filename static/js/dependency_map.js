// Dependency Map — Cytoscape.js initialization, styling, layout, interactions.
// Risk levels/scores come from the backend (Phase 4 engine). No risk math here.

(function () {
  "use strict";

  var RISK_COLORS = {
    critical: "#d32f2f",
    high: "#f57c00",
    medium: "#f9a825",
    low: "#388e3c",
    none: "#9e9e9e",
  };

  var BACKUP_EDGE_COLOR = {
    no_backup: "#d32f2f",
    backup_unknown: "#f9a825",
    has_backup: "#388e3c",
  };

  var PERSON_LOAD_COLOR = {
    high: "#d32f2f",
    medium: "#f57c00",
    low: "#2563eb",
  };

  var container = document.getElementById("wr-cy");
  if (!container) return;

  fetch("/api/dependency-map")
    .then(function (r) { return r.json(); })
    .then(function (data) { render(data); })
    .catch(function (err) {
      container.innerHTML =
        '<p class="wr-empty">Could not load the dependency map.</p>';
      console.error(err);
    });

  function render(data) {
    var elements = [];
    data.nodes.forEach(function (n) { elements.push(n); });
    data.edges.forEach(function (e) { elements.push(e); });

    var cy = cytoscape({
      container: container,
      elements: elements,
      wheelSensitivity: 0.2,
      style: [
        // Person nodes — size scales with critical asset count, color by load.
        {
          selector: 'node[type="person"]',
          style: {
            "shape": "ellipse",
            "background-color": function (ele) {
              return PERSON_LOAD_COLOR[ele.data("risk_load")] || "#2563eb";
            },
            "label": "data(label)",
            "color": "#fff",
            "text-valign": "center",
            "text-halign": "center",
            "font-size": "11px",
            "text-wrap": "wrap",
            "text-max-width": "80px",
            "width": function (ele) {
              return 40 + 14 * (ele.data("critical_asset_count") || 0);
            },
            "height": function (ele) {
              return 40 + 14 * (ele.data("critical_asset_count") || 0);
            },
            "border-width": function (ele) {
              return (ele.data("uncovered_count") || 0) > 0 ? 4 : 0;
            },
            "border-color": "#b71c1c",
          },
        },
        // Asset nodes — rounded rectangle, border by risk level, thickness by criticality.
        {
          selector: 'node[type="asset"]',
          style: {
            "shape": "round-rectangle",
            "background-color": "#ffffff",
            "label": "data(label)",
            "color": "#222",
            "text-valign": "center",
            "text-halign": "center",
            "font-size": "10px",
            "text-wrap": "wrap",
            "text-max-width": "90px",
            "width": "label",
            "height": "36px",
            "padding": "8px",
            "border-width": function (ele) {
              var c = ele.data("criticality");
              if (c === "critical") return 5;
              if (c === "high") return 4;
              return 2;
            },
            "border-color": function (ele) {
              return RISK_COLORS[ele.data("risk_level")] || RISK_COLORS.none;
            },
          },
        },
        // Function nodes — flat bars.
        {
          selector: 'node[type="function"]',
          style: {
            "shape": "round-rectangle",
            "background-color": "#eceff1",
            "label": "data(label)",
            "color": "#37474f",
            "text-valign": "center",
            "text-halign": "center",
            "font-size": "10px",
            "text-wrap": "wrap",
            "text-max-width": "100px",
            "width": "label",
            "height": "28px",
            "padding": "6px",
            "border-width": 1,
            "border-color": "#b0bec5",
          },
        },
        // Primary edges — solid, colored by backup status.
        {
          selector: 'edge[edge_type="primary"]',
          style: {
            "width": 2.5,
            "line-color": function (ele) {
              return BACKUP_EDGE_COLOR[ele.data("backup_status")] || RISK_COLORS.none;
            },
            "target-arrow-color": function (ele) {
              return BACKUP_EDGE_COLOR[ele.data("backup_status")] || RISK_COLORS.none;
            },
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            "label": "data(label)",
            "font-size": "9px",
            "color": "#555",
            "text-background-color": "#fff",
            "text-background-opacity": 1,
            "text-background-padding": "1px",
          },
        },
        // Backup edges — dashed, green-ish, distinct from primary.
        {
          selector: 'edge[edge_type="backup"]',
          style: {
            "width": 2,
            "line-style": "dashed",
            "line-color": "#388e3c",
            "target-arrow-color": "#388e3c",
            "target-arrow-shape": "triangle-tee",
            "curve-style": "bezier",
            "opacity": 0.8,
          },
        },
        // Asset -> function edges — thin, neutral.
        {
          selector: 'edge[edge_type="category"]',
          style: {
            "width": 1,
            "line-color": "#cfd8dc",
            "target-arrow-shape": "none",
            "curve-style": "bezier",
          },
        },
      ],
      layout: {
        name: "breadthfirst",
        directed: true,
        roots: 'node[type="person"]',
        spacingFactor: 1.3,
        padding: 20,
      },
    });

    // Tooltip via native title on the container (simple, demo-friendly).
    var tip = document.createElement("div");
    tip.className = "wr-cy-tooltip";
    tip.style.display = "none";
    document.body.appendChild(tip);

    cy.on("mouseover", "node", function (evt) {
      var d = evt.target.data();
      var html = "";
      if (d.type === "person") {
        html = "<strong>" + d.label + "</strong>" +
          (d.role ? "<br>" + d.role : "") +
          "<br>Critical/High assets: " + d.critical_asset_count +
          "<br>No-backup responsibilities: " + d.uncovered_count;
      } else if (d.type === "asset") {
        html = "<strong>" + d.label + "</strong>" +
          "<br>Risk: " + d.risk_level + " (" + d.risk_score + ")" +
          "<br>Criticality: " + d.criticality;
      } else {
        html = "<strong>" + d.label + "</strong>";
      }
      tip.innerHTML = html;
      tip.style.display = "block";
    });

    cy.on("mouseover", 'edge[edge_type="primary"]', function (evt) {
      var d = evt.target.data();
      tip.innerHTML = "<strong>" + (d.responsibility_type || "") + "</strong>" +
        "<br>Backup: " + (d.backup_status || "").replace(/_/g, " ");
      tip.style.display = "block";
    });

    cy.on("mousemove", function (evt) {
      tip.style.left = (evt.originalEvent.pageX + 12) + "px";
      tip.style.top = (evt.originalEvent.pageY + 12) + "px";
    });

    cy.on("mouseout", "node, edge", function () {
      tip.style.display = "none";
    });

    // Click navigation.
    cy.on("tap", "node", function (evt) {
      var d = evt.target.data();
      if (d.type === "person") {
        window.location.href = "/people/" + d.entity_id;
      } else if (d.type === "asset") {
        window.location.href = "/assets/" + d.entity_id;
      }
      // function nodes: no action
    });
  }
})();

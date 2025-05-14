// GelSight image viewer call back functions
// Created by Alan Zhao (alanzhao@csail.mit.edu)

function createTabContent(setting_name, setting_value, parent_id) {
    var div = document.createElement("div");
    div.classList.add("setting-div");
    var label = document.createElement("p");
    label.classList.add("setting-label");
    label.innerHTML = setting_name;
    div.appendChild(label);
    if (parent_id !== "") {
        parent_id += "-";
    }
    if (typeof setting_value === "string") {
        var content = document.createElement("input");
        content.type = "text";
        content.value = setting_value;
        content.id = parent_id + setting_name;
        content.classList.add("text-input");
        content.classList.add("single-input");
        div.appendChild(content);
    } else if (typeof setting_value === "number") {
        var content = document.createElement("input");
        content.type = "number";
        content.value = setting_value;
        content.id = parent_id + setting_name;
        content.classList.add("number-input");
        content.classList.add("single-input");
        div.appendChild(content);
    } else if (typeof setting_value === "boolean") {
        var content = document.createElement("input");
        content.type = "checkbox";
        content.checked = setting_value;
        content.id = parent_id + setting_name;
        content.classList.add("checkbox-input");
        content.classList.add("single-input");
        div.appendChild(content);
    } else if (Array.isArray(setting_value)) {
        var subdiv = document.createElement("div");
        subdiv.id = parent_id + setting_name;
        subdiv.classList.add("array-input");
        for (var i = 0; i < setting_value.length; i++) {
            var content = document.createElement("input");
            content.type = (typeof setting_value[i] === "string") ? "text" : "number";
            content.value = setting_value[i];
            content.classList.add(content.type + "-input");
            content.classList.add("array-input-element");
            subdiv.appendChild(content);
        }
        div.appendChild(subdiv);
    } else if (typeof setting_value === "object") {
        var subdiv = document.createElement("div");
        for (var key in setting_value) {
            var content = createTabContent(key, setting_value[key], parent_id + setting_name);
            subdiv.appendChild(content);
        }
        div.appendChild(subdiv);
    }
    return div;
}

function openSetting(event, setting_name) {
    let tabcontents = document.querySelectorAll(".tab-content");
    for (let tabcontent of tabcontents) {
        tabcontent.classList.add("hidden");
    }
    let tablinks = document.querySelectorAll(".tab-link");
    for (let tablink of tablinks) {
        tablink.classList.remove("active");
    }
    document.querySelector("#" + setting_name).classList.remove("hidden");
    event.currentTarget.classList.add("active");
}

function createNewSettingTab(setting_name, setting_value) {
    // create a tab link
    var tab = document.createElement("button");
    tab.className = "tab-link";
    tab.id = setting_name + "-tab-btn";
    tab.innerHTML = setting_name;
    tab.onclick = (event) => {openSetting(event, setting_name);};
    document.getElementById("tab-links").appendChild(tab);

    // create a tab content
    let content = document.createElement("div");
    content.classList.add("tab-content", "hidden");
    content.id = setting_name;
    content.appendChild(createTabContent(setting_name, setting_value, ""));
    document.getElementById("tab-contents").appendChild(content);

}

function updateSettings(json) {
    // clear the tab links and tab contents
    const activated = document.querySelector(".tab-link.active");
    let activated_id = null;
    if (activated !== null) {
        activated_id = activated.id;
    }
    document.getElementById("tab-links").innerHTML = "";
    document.getElementById("tab-contents").innerHTML = "";
    console.log("Reponse json: ");
    console.log(json);
    for (var key in json) {
        createNewSettingTab(key, json[key]);
    }
    // open the last activated tab or the first tab
    if (activated_id !== null && document.querySelector("#" + activated_id) !== null) {
        document.querySelector("#" + activated_id).click();
    } else {
        document.querySelector("#tab-links button").click();
    }
}

function fetchSettings() {
    fetch("/settings", {method: "GET"})
    .then((response) => response.json())
    .then((json) => updateSettings(json));
}

const fetchBtn = document.getElementById("btn-fetch");
fetchBtn.addEventListener("click", () => {
    fetchSettings();
});

const resetBtn = document.getElementById("btn-reset");
resetBtn.addEventListener("click", () => {
    fetch("/reset-settings", {
        method: "GET",
        headers: {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    })
    .then((response) => response.json())
    .then((json) => fetchSettings());
});

function parseIdToSettingName(id, setting_obj, val) {
    // if '-' is in the id, it is a nested setting
    const hypen_index = id.indexOf("-");
    if (hypen_index >= 0) {
        const cur_setting = id.slice(0, hypen_index);
        const next_id = id.slice(hypen_index + 1);

        if (setting_obj[cur_setting] === undefined) {
            setting_obj[cur_setting] = {};
        }
        parseIdToSettingName(next_id, setting_obj[cur_setting], val);
    } else {
        setting_obj[id] = val;
    }
}

const uploadBtn = document.getElementById("btn-upload");
uploadBtn.addEventListener("click", () => {
    const data = {};
    const setting_inputs = document.querySelectorAll(".single-input");
    // split the id to get the setting name
    for (const setting_input of setting_inputs) {
        let value = setting_input.value;
        if (setting_input.type === "number") {
            value = parseFloat(value);
        } else if (setting_input.type === "checkbox") {
            value = setting_input.checked;
        }
        parseIdToSettingName(setting_input.id, data, value);
    }
    const array_inputs = document.querySelectorAll(".array-input");
    for (const array_input of array_inputs) {
        const array = [];
        const array_elements = array_input.querySelectorAll(".array-input-element"); // returns in document order
        for (const array_element of array_elements) {
            let value = array_element.value;
            if (array_element.type === "number") {
                value = parseFloat(value);
            } else if (array_element.type === "checkbox") {
                value = array_element.checked;
            }
            array.push(value);
        }
        parseIdToSettingName(array_input.id, data, array);
    }
    console.log(data);
    fetch("/settings", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
    })
    .then((response) => response.json())
    .then((json) => {console.log(json); fetchSettings()});
});

fetchSettings();
uploadBtn.click();
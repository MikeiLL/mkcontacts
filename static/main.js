import {
    lindt,
    choc,
    replace_content,
    on,
    DOM,
} from "https://rosuav.github.io/choc/factory.js";
const {BUTTON, FORM, INPUT, LABEL, SPAN, TABLE, TBODY, TD, TH, TR} = lindt; //autoimport
import {simpleconfirm} from "./utils.js";

export function render(state) {
    replace_content("main", [
        FORM({id: "newcontact"}, (
        TABLE(TBODY([
            state.contacts.map((c, idx) => TR({'data-idx': idx}, [
                TH(c.fullname), TD(c.email), TD(c.phone), TD(BUTTON({'data-id': c.id, type: "button", class: "delete",},"x"))
            ])),
            TR({class: "contactinputrow"},[
                TH([
                    LABEL([SPAN("fullname"), INPUT({type: "text", name: "fullname", autocomplete: "off"})])
                ]), TD(
                    LABEL([SPAN("email"), INPUT({type: "text", name: "email", autocomplete: "off", type: "email"})])
                ), TD(
                    LABEL([SPAN("phone"), INPUT({type: "text", name: "phone", autocomplete: "off"})])
                ), TD(
                    BUTTON({id: "btnnew", type: "submit"}, "new")
                )])
        ])))), // end form
    ]);
}
on("click", "#btnnew", async (e) => {
    e.preventDefault();
    const contactForm = e.match.closest("#newcontact");
    fetch("/newcontact", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            form: JSON.stringify(Object.fromEntries(new FormData(contactForm)))
        }),
    })
    contactForm.reset();
});

on("click", ".delete", simpleconfirm("Delete contact?", async (e) => {
    e.preventDefault();
    fetch("/deletecontact", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            id: e.match.dataset.id
        }),
    })
}))

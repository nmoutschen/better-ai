// Adds items to the pick-up basket kept in localStorage.
const basket = JSON.parse(localStorage.getItem("basket") || "[]");
const count = document.getElementById("basket-count");
count.textContent = basket.length;

document.querySelectorAll("button.add").forEach((button) => {
  button.addEventListener("click", () => {
    basket.push(button.dataset.item);
    localStorage.setItem("basket", JSON.stringify(basket));
    count.textContent = basket.length;
  });
});

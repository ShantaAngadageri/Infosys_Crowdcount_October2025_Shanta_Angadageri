document.addEventListener('DOMContentLoaded', function () {
  fetch('/users_data')
    .then((response) => response.json())
    .then((data) => {
      const users = data.users;
      const tableBody = document.querySelector('#userTable tbody');
      tableBody.innerHTML = '';
      users.forEach((user) => {
        const spanClass = user.status === 'Active' ? 'Active' : 'Inactive';
        const row = document.createElement('tr');
        row.innerHTML = `
          <td>${user.first_name}</td>
          <td>${user.role}</td>
          <td><span class="${spanClass}">${user.status}</span></td>
        `;
        tableBody.appendChild(row);
      });
    });
});

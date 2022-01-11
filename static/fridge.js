$('.delete-ing').click(deleteIng)

async function deleteIng() {
    const id = $(this).data('id')
    await axios.delete(`/fridge/ingredient/remove/${id}`)
    $(this).parent().remove()
}
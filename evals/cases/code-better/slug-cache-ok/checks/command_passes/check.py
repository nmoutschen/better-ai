from text import slugify
slugify.cache_clear()
assert slugify('Hello World') == 'hello-world'
hits = slugify.cache_info().hits
assert slugify('Hello World') == 'hello-world'
assert slugify.cache_info().hits == hits + 1, 'a repeated title is not served from the cache'
assert slugify('Second Post') == 'second-post'

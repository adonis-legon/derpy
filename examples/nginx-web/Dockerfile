FROM nginx:alpine

# Create a custom index page
RUN echo "<html><body><h1>Hello from Derpy!</h1><p>This container was built with Derpy, an independent container tool.</p></body></html>" > /usr/share/nginx/html/index.html

# Start nginx
CMD ["nginx", "-g", "daemon off;"]

FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
ARG VITE_GIT_COMMIT=dev
ARG VITE_BUILD_TIME=
ENV VITE_GIT_COMMIT=$VITE_GIT_COMMIT
ENV VITE_BUILD_TIME=$VITE_BUILD_TIME
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

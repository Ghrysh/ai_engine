FROM php:8.4-fpm

RUN apt-get update && apt-get install -y \
    git curl libpng-dev libonig-dev libxml2-dev zip unzip libpq-dev

RUN docker-php-ext-install pdo_pgsql mbstring exif pcntl bcmath gd

RUN chmod 777 /tmp

RUN echo "error_reporting = E_ALL & ~E_NOTICE & ~E_DEPRECATED" >> /usr/local/etc/php/conf.d/error_reporting.ini

WORKDIR /var/www
